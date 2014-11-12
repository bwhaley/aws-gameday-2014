#!/usr/local/bin/python

import troposphere
import troposphere.ec2 as ec2
import troposphere.sqs as sqs
import troposphere.s3 as s3
from troposphere import GetAtt, Output, Ref
from awacs.aws import Allow, Everybody, Policy, Statement, AWSPrincipal, Action, Principal
import awacs.sqs

AWS_ACCESS_KEY_ID = "YOURKEYHERE"
AWS_SECRET_ACCESS_KEY = "YOURSECRETHERE"
CIDR = "10.0.0.0/16"
PUBLIC = "10.0.0.0/24"
PRIVATE = "10.0.1.0/24"
REGION = "someregion"
ZONE = "somezone"
NAT_INSTANCE_TYPE = "m1.small"
NAT_AMI = "someami"
KEY_PAIR_NAME = "gameday"
VPC_NAME = "GamedayVPC"
INPUT_Q = "input"
OUTPUT_Q = "output"
BUCKET_NAME = "image-bucket-somenumber"

t = troposphere.Template()

t.add_resource(ec2.VPC(
    VPC_NAME,
    CidrBlock=CIDR,
    EnableDnsHostnames=True,
    EnableDnsSupport=True
))

t.add_resource(ec2.Subnet(
    "PublicSubnet",
    VpcId=Ref(VPC_NAME),
    CidrBlock=PUBLIC,
    AvailabilityZone=ZONE
))

t.add_resource(ec2.Subnet(
    "PrivateSubnet",
    VpcId=Ref(VPC_NAME),
    CidrBlock=PRIVATE,
    AvailabilityZone=ZONE
))

t.add_resource(ec2.InternetGateway('InternetGateway'))
t.add_resource(ec2.VPCGatewayAttachment(
    'VPCGatewayAttachment',
    VpcId=Ref(VPC_NAME),
    InternetGatewayId=Ref('InternetGateway'),
    DependsOn='InternetGateway'
))

t.add_resource(ec2.RouteTable(
    'PublicRouteTable',
    VpcId=Ref(VPC_NAME)
))

# default public route
t.add_resource(ec2.Route(
    'DefaultPublicRoute',
    RouteTableId=Ref('PublicRouteTable'),
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=Ref('InternetGateway'),
    DependsOn='VPCGatewayAttachment'
))

# associate public subnets with public route table
t.add_resource(ec2.SubnetRouteTableAssociation(
    'PublicAssociation',
    SubnetId=Ref('PublicSubnet'),
    RouteTableId=Ref('PublicRouteTable')
))

t.add_resource(ec2.RouteTable(
    'PrivateRouteTable',
    VpcId=Ref(VPC_NAME)
))
t.add_resource(ec2.Route(
    'DefaultPrivateRoute',
    RouteTableId=Ref('PrivateRouteTable'),
    DestinationCidrBlock='0.0.0.0/0',
    InstanceId=Ref('Nat'),
    DependsOn='Nat'
))

t.add_resource(ec2.SubnetRouteTableAssociation(
    'PrivateRouteAssociation',
    SubnetId=Ref('PrivateSubnet'),
    RouteTableId=Ref('PrivateRouteTable')
))


t.add_resource(ec2.SecurityGroup(
    'NatSG',
    GroupDescription='Security group for NAT host.',
    VpcId=Ref(VPC_NAME)
))

t.add_resource(ec2.SecurityGroupIngress(
    'NatSSHIngress',
    GroupId=Ref('NatSG'),
    IpProtocol='tcp',
    FromPort='22',
    ToPort='22',
    CidrIp='0.0.0.0/0'
))

t.add_resource(ec2.SecurityGroupIngress(
    'NatHTTPIngress',
    GroupId=Ref('NatSG'),
    IpProtocol='tcp',
    FromPort='80',
    ToPort='80',
    CidrIp='10.0.1.0/24'
))

t.add_resource(ec2.SecurityGroupIngress(
    'NatHTTPSIngress',
    GroupId=Ref('NatSG'),
    IpProtocol='tcp',
    FromPort='443',
    ToPort='443',
    CidrIp='10.0.1.0/24'
))

t.add_resource(ec2.EIP(
    'NatEIP',
    Domain='vpc',
    InstanceId=Ref('Nat'),
    DependsOn='VPCGatewayAttachment'
))

t.add_resource(ec2.Instance(
    'Nat',
    ImageId=NAT_AMI,
    InstanceType=NAT_INSTANCE_TYPE,
    KeyName=KEY_PAIR_NAME,
    SourceDestCheck=False,
    SubnetId=Ref('PublicSubnet'),
    SecurityGroupIds=[Ref('NatSG')]
))

## Queues

t.add_resource(sqs.Queue(INPUT_Q, QueueName=INPUT_Q, VisibilityTimeout=90))
t.add_resource(sqs.Queue(OUTPUT_Q, QueueName=OUTPUT_Q, VisibilityTimeout=90))

q_policy= Policy( 
    Statement=[
        Statement(
            Sid='2',
            Effect=Allow,
            Principal=AWSPrincipal("526039161745"),
            Action=[ awacs.sqs.SendMessage ],
            Resource=["arn:aws:sqs:ap-northeast-1:<accountnum>:input"]
        ),
    ],
)

t.add_resource(troposphere.sqs.QueuePolicy(
    'BatchQueuePolicy',
    PolicyDocument=q_policy,
    Queues=[Ref(INPUT_Q)]
))


t.add_resource(s3.Bucket(
    "S3Bucket",
    BucketName=BUCKET_NAME,
    AccessControl=s3.Private
))

print t.to_json()
