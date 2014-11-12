#!/usr/local/bin/python

import base64
import troposphere
import troposphere.ec2 as ec2
import troposphere.iam as iam
import troposphere.s3 as s3
import troposphere.cloudwatch as cloudwatch
import troposphere.autoscaling as autoscale
from troposphere import GetAtt, Output, Ref
from awacs.aws import Allow, Everybody, Policy, Statement, AWSPrincipal, Action, Principal
import awacs.sqs
import awacs.s3

AWS_ACCESS_KEY_ID = "YOURKEYHERE"
AWS_SECRET_ACCESS_KEY = "YOURSECRETHERE"
WORKER_AMI = "someami"
INSTANCE_TYPE = "t2.micro"
AVAILABILITY_ZONES = "someregion"
SUBNETS = "subnet-9db04bea"
VPC_ID = "vpc-33669a56"
KEY_NAME = "gameday"
REGION = "ap-northeast-1"
ACCOUNT = "accountnum"
USER_DATA = base64.b64encode("""
#!/bin/sh
/usr/bin/python /home/ec2-user/image_processor.py &
""")
INPUT_Q = "input"


t = troposphere.Template()

assume_role_policy = Policy(
    Statement=[
        Statement(
            Effect=Allow,
            Principal=Principal('Service', 'ec2.amazonaws.com'),
            Action=[Action('sts', 'AssumeRole')]
        )
    ]
)

t.add_resource(iam.PolicyType(
    'BatchProcessingPolicy',
    PolicyName='BatchProcessing',
    PolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[Action("s3", "*")],
                Resource=[awacs.s3.S3_ARN("*"), ]
            ),
            Statement(
                Effect=Allow,
                Action=[Action("sqs", "*")],
                Resource=[awacs.sqs.SQS_ARN(REGION, ACCOUNT, "*"), ]
            )
       ]
    ),
    Roles=[Ref('BatchProcessingRole')]
))

t.add_resource(iam.Role(
    'BatchProcessingRole',
    AssumeRolePolicyDocument=assume_role_policy,
    Path='/'
))

t.add_resource(iam.InstanceProfile(
    'BatchProcessingProfile',
    Path='/',
    Roles=[Ref('BatchProcessingRole')]
))

t.add_resource(ec2.SecurityGroup(
    'BatchProcessingSG',
    GroupDescription='Security Group for Batch processing workers',
    VpcId=VPC_ID
))

t.add_resource(ec2.SecurityGroupIngress(
    'BatchSSHIngress',
    GroupId=Ref('BatchProcessingSG'),
    IpProtocol='tcp',
    FromPort='22',
    ToPort='22',
    CidrIp='0.0.0.0/0'
))

t.add_resource(autoscale.ScalingPolicy(
    'ScaleOutPolicy',
    AdjustmentType='ChangeInCapacity',
    ScalingAdjustment='1',
    AutoScalingGroupName=Ref('AutoscaleGroup'),
    Cooldown=30
))

# Scale in by 1 node every 30 seconds
t.add_resource(autoscale.ScalingPolicy(
    'ScaleInPolicy',
    AdjustmentType='ChangeInCapacity',
    ScalingAdjustment='-1',
    AutoScalingGroupName=Ref('AutoscaleGroup'),
    Cooldown=30
))

dimension = cloudwatch.MetricDimension(
    'MetricDimension',
    Name="QueueName",
    Value=INPUT_Q
)

threshold = 10

t.add_resource(cloudwatch.Alarm(
    'QueueDepthAlarm',
    AlarmDescription="Queue depth above threshold",
    AlarmActions=[Ref('ScaleOutPolicy')],
    OKActions=[Ref('ScaleInPolicy')],
    Statistic='Average',
    Period=60,
    Threshold=threshold,
    EvaluationPeriods=1,
    ComparisonOperator='GreaterThanThreshold',
    MetricName='ApproximateNumberOfMessagesVisible',
    Namespace='AWS/SQS',
    Dimensions=[dimension],
))


t.add_resource(autoscale.LaunchConfiguration(
    'LaunchConfiguration',
    ImageId=WORKER_AMI,
    UserData=USER_DATA,
    SecurityGroups=[Ref('BatchProcessingSG')],
    KeyName=KEY_NAME,
    InstanceType=INSTANCE_TYPE,
    IamInstanceProfile=Ref('BatchProcessingProfile')
))

t.add_resource(autoscale.AutoScalingGroup(
    'AutoscaleGroup',
    AvailabilityZones=[AVAILABILITY_ZONES],
    VPCZoneIdentifier=[SUBNETS],
    LaunchConfigurationName=Ref('LaunchConfiguration'),
    MinSize='1',
    MaxSize='4',
    Cooldown=30
))

print t.to_json()
