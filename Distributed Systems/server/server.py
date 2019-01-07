# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: Christoffer Olsson
# Student: Alex Nitsche
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread
#from copy import deepcopy
import copy

from bottle import Bottle, run, request, template
import requests

# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()
    board = {}
    # status: 0 = unassigned, 1= attacking 2=retreating 3=byzantine
    status = 0

    # The lists gets filled with n 'None' in main, where n is the total number of nodes
    #responce_vector is the vector with all the votes of the nodes
    #all_vectors is the vector with all the responce_vectors of the nodes
    response_vector=[]
    all_vectors=[]

    #True for attack to win a tie, False for retreat to win a tie
    tie_breaker_value = True

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # should be given to the students?
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload, req):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                #print("in contact vessel POST")#debugtool
                res = requests.post('http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                #print ("in contact_vessel GET")#debugtool
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload, req):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    #a modification of propagate_to_vessels, it allows the "entry" values
    #to be changed and thus sending different entry's to the different nodes
    def byzantine_propagate(path, payload, req, byzantine_entries):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself

                #change the entry parameter in the payload
                payload["entry"]=byzantine_entries[int(vessel_id)-1]

                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        #print ("in / (route)")#debugtool
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()), members_name_string='Group 97')

    # ------------------------------------------------------------------------------------------------------
    # BYZANTINE ALGORITHM
    # ------------------------------------------------------------------------------------------------------

    #Simple methods that the byzantine node calls to decide what to vote.

    #Compute byzantine votes for round 1, by trying to create
    #a split decision.
    #input:
    #	number of loyal nodes,
    #	number of total nodes,
    #	Decision on a tie: True or False
    #output:
    #	A list with votes to send to the loyal nodes
    #	in the form [True,False,True,.....]
    def compute_byzantine_vote_round1(no_loyal,no_total,on_tie):

      result_vote = []
      for i in range(0,no_loyal):
        if i%2==0:
          result_vote.append(not on_tie)
        else:
          result_vote.append(on_tie)
      return result_vote

    #Compute byzantine votes for round 2, trying to swing the decision
    #on different directions for different nodes.
    #input:
    #	number of loyal nodes,
    #	number of total nodes,
    #	Decision on a tie: True or False
    #output:
    #	A list where every element is a the vector that the
    #	byzantine node will send to every one of the loyal ones
    #	in the form [[True,...],[False,...],...]
    def compute_byzantine_vote_round2(no_loyal,no_total,on_tie):

      result_vectors=[]
      for i in range(0,no_loyal):
        if i%2==0:
          result_vectors.append([on_tie]*no_total)
        else:
          result_vectors.append([not on_tie]*no_total)
      return result_vectors

    #what happens when some one votes attack
    @app.post('/vote/attack')
    def is_attacking():
        global status,node_id
        try:
            #set my status and add my vote to my responce_vector
            status= 1
            response_vector[int(node_id)-1]= True

            #Propagate the update to all the other vessels
            path = '/vote/receive/first'
            tempdict = {"entry" : True, "id": node_id} #True = Attack
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()

            #If we have an action from each of the nodes, then everyone has voted and
            #its time for the second round and we send our response_vector vector to the other nodes
            if response_vector.count(None)==0:

                #store our own list in the all list
                all_vectors[node_id -1] = response_vector

                #send my vector
                path = '/vote/receive/second'
                tempdict = {"entry" : response_vector, "id": node_id}
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()

            return "Attacking"
        except Exception as e:
            print e
        return False

    #what happens when some one votes retreat
    @app.post('/vote/retreat')
    def is_retreating():
        global status
        try:
            #set my status and add my vote to my responce_vector
            status= 2
            response_vector[int(node_id)-1]= False

            #Propagate the update to all the other vessels
            path = '/vote/receive/first'
            tempdict = {"entry" : False, "id": node_id} #False = Retreat
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()


            #if we have an action from each of the nodes, then everyone has voted and
            #its time for the second round and we send our response_vector vector to the other nodes
            if response_vector.count(None)==0:

                #store our own list in the all list
                all_vectors[node_id -1] = response_vector

                #send my vector
                path = '/vote/receive/second'
                tempdict = {"entry" : response_vector, "id": node_id}
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()

            return "Retreating"
        except Exception as e:
            print e
        return False

    #what the byzantine does
    @app.post('/vote/byzantine')
    def is_byzantine():
        global status, amount_of_vessels

        #set status
        status= 3

        #creates a list of the responses for all nodes (including itself for
        #simplicity since it makes the list the right length for the
        #byzantine_propagate method and for the chek to enter the second phase)
        byzantine_response = compute_byzantine_vote_round1(amount_of_vessels-1, amount_of_vessels, tie_breaker_value)
        print "Byzantine responses: " + str(byzantine_response) #debug

        #store a value for us in responces and byzantine_responses(neded inorder to make the
        #lists into the right length, its our own value and wont be sent to the other nodes anyway)
        response_vector[node_id-1] = not tie_breaker_value
        byzantine_response.insert(node_id-1, not tie_breaker_value)

        print "Byzantine Response vector: " + str(byzantine_response) #debug

        #propagate the update to all the other vessels via the byzantine_propagate method
        path = '/vote/receive/first'
        tempdict = {"entry" : False, "id": node_id} #True = Attack
        thread = Thread(target=byzantine_propagate, args=(path, tempdict, 'POST', byzantine_response))
        thread.daemon=True
        thread.start()

        #if we have an action from each of the nodes,its time for the second round
        #and time to generate our byzantine response vectors
        if response_vector.count(None)==0:

            #generate byzantine votes and add our vector to our all_vectors
            byzantine_vectors=compute_byzantine_vote_round2(amount_of_vessels-1,amount_of_vessels,tie_breaker_value)
            all_vectors[node_id-1] = response_vector

            #pad byzantine_vectors so it has the right length (by including our value,
            #and it wont be sent by byzantine_propagate anyway)
            byzantine_vectors.insert(node_id-1,response_vector)

            #propegate to the other vessels via a special byzantine_propegate method
            print "byzantine_vectors: " + str(byzantine_vectors)
            path = '/vote/receive/second'
            tempdict = {"entry" : byzantine_response, "id": node_id} #True = Attack
            thread = Thread(target=byzantine_propagate, args=(path, tempdict, 'POST', byzantine_vectors) )
            thread.daemon=True
            thread.start()

        return "Byzantineing"


    @app.get('/vote/result')
    def vote_result():
        global all_vectors, tie_breaker_value

        #size is the size of the vector of all vectors and it's also the total number of nodes
        size = len(all_vectors)

        #instansiate the final_result_vector and the final result
        final_result_vector = []
        final_result = ""

        #filling the vector with None for easier manipulation of the vector
        for i in range(0,size):
            final_result_vector.append(None)

        if all_vectors.count(None)==0:

            #inside_index in the outer for since we want colums not rows
            for inside_index in range(0, size):

                #running counter, used to count the amount of True and False values
                counter = 0
                for outside_index in range(0, size):
                    #ignore the "diagonal"
                    if inside_index != outside_index:

                        #if the value is True add 1 to the counter, else subtract 1
                        if all_vectors[outside_index][inside_index]:
                            counter = counter + 1
                        else:
                            counter = counter - 1
                        print "inside_index: "+str(inside_index) + " outside_index: " +str(outside_index) +" counter: "+ str(counter)
                #evaluate the counter and place the result in the final_result_vector
                if counter > 0:
                    final_result_vector[inside_index] = True
                elif counter < 0:
                    final_result_vector[inside_index] = False
                else:
                    final_result_vector[inside_index] = tie_breaker_value
                print "majority (or tie) is: " + str(final_result_vector[inside_index])

            #count and return the final_result_vector and return a verdict
            finalcounter = 0
            for final_index in range(0, size):
                if final_result_vector[final_index]:
                    finalcounter = finalcounter + 1
                else:
                    finalcounter = finalcounter - 1

            if finalcounter + int(tie_breaker_value) > 0:
                final_result = "Everyone is Attacking"
            elif finalcounter <= 0:
                final_result = "Everyone is Waiting"
            return "Result vector: " + str(final_result_vector) + " Verdict: " + final_result

        #if the all_vectors vector contains a null, then not every node has voted yet
        else:
            return "Not every one has voted"

    #what happens during the first election cycle of the algorithm
    @app.post('/vote/receive/first')
    def receive_from_other():
        global response_vector, status,all_vectors
        try:
            #get the entry and id of sender
            entry = request.forms.get("entry")
            id = request.forms.get("id")

            #string comparision since entry is a string (cleaning the value)
            response_vector[int(id)-1]= entry== 'True'

            #If we have an action from each of the nodes,
            #its time for the second round of the algorithm and we check
            #the status to se if this node is a byzantine (since byzantines does byzantine stuff)
            if response_vector.count(None)==0:
                if status != 3:

                    #store the received list in the all-list list
                    all_vectors[node_id -1] = response_vector

                    path = '/vote/receive/second'
                    tempdict = {"entry" : response_vector, "id": node_id} #True = Attack
                    thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                    thread.daemon=True
                    thread.start()
                else:

                    #generate byzantine votes and insert our own
                    byzantine_vectors=compute_byzantine_vote_round2(amount_of_vessels-1,amount_of_vessels,tie_breaker_value)
                    all_vectors[node_id-1] = response_vector

                    #pad byzantine_vectors so it has the right length (by including our value, and it wont be sent anyway)
                    byzantine_vectors.insert(node_id-1,response_vector)

                    #propegate to the other vessels via a special byzantine_propegate method
                    path = '/vote/receive/second'
                    tempdict = {"entry" : response_vector, "id": node_id} #True = Attack
                    thread = Thread(target=byzantine_propagate, args=(path, tempdict, 'POST', byzantine_vectors) )
                    thread.daemon=True
                    thread.start()

            return {"entry":entry, "id":id}
        except Exception as e:
            print e
        return False


    @app.post('/vote/receive/second')
    def receive_from_other_all():
        global all_vectors
        try:
            #get the entries and the id of the sender
            entry = request.forms.getall("entry")
            id = request.forms.get("id")

            #need to clean up the entry since request.form.getall returns the
            #list of bools as a list of strings
            for index in range(0, len(entry)):
                entry[index]= entry[index]=='True'

            #add the cleaned entry to the list of all vectors
            all_vectors[int(id)-1]= entry

            return {"entry":entry, "id":id}
        except Exception as e:
            print e
        return False

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post Give it to the students
    # Execute the code
    def main():
        global vessel_list, node_id, app,amount_of_vessels,response_vector, all_vectors

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        amount_of_vessels = args.nbv -1

        for i in range(1, args.nbv): #fills the vectors with "None" as placeholder values
            response_vector.append(None)
            all_vectors.append(None)


        vessel_list = dict()
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
            time.sleep(60.)
