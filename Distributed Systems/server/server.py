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
    response_vector=[]
    all_vectors=[]
    tie_breaker_value = True #True for attack to win a tie, False for retreat to win a tie


    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Should nopt be given to the student
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            #print ("in add_new_element_to_store")#debugtool

            board.update({entry_sequence: element})
            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            #print ("in modify_element_in_store") #debugtool

            board[entry_sequence]=modified_element
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            #print ("in delete_element_from_store")#debugtool
            del board[entry_sequence]
            success = True
        except Exception as e:
            print e
        return success

        #new_post_number checks for the first avaviable key and returns it
    def new_post_number():
        i = 0
        while board.has_key(i):
            i += 1
        return i

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
        print "Entry in payload: " + str(payload["entry"])#debugtool
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    #a modification of propagate_to_vessels, it allows the "entry" values
    #to be changed and thus sending different "entry"s to the other nodes
    def byzantine_propagate(path, payload, req, byzantine_entries):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself

                print "Vessel_id: " + str(vessel_id)#debug
                print "byzantine_entries: " + str(byzantine_entries)#debug
                #change the entry parameter in the payload

                print str(byzantine_entries[int(vessel_id)-1])
                payload["entry"]=byzantine_entries[int(vessel_id)-1]

                print str(payload["entry"])
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


    @app.post('/vote/attack')
    def is_attacking():
        global status,node_id
        try:
            status= 1
            response_vector[int(node_id)-1]= True
            print "Attack response_vector: " + str(response_vector) #debugg

            #Propagate the update to all the other vessels
            path = '/vote/receive/first'
            tempdict = {"entry" : True, "id": node_id} #True = Attack
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()

            #If we have an action from each of the nodes,
            #its time for the second round and we send our response_vector vector to the other nodes
            if response_vector.count(None)==0:

                #store our own list in the all list
                all_vectors[node_id -1] = response_vector

                path = '/vote/receive/second'
                tempdict = {"entry" : response_vector, "id": node_id} #True = Attack
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()

            return "Attacking"
        except Exception as e:
            print e
        return False


    @app.post('/vote/retreat')
    def is_retreating():
        global status
        try:
            status= 2
            response_vector[int(node_id)-1]= False
            print "Retreat response_vector" + str(response_vector) #debugg

            #Propagate the update to all the other vessels
            path = '/vote/receive/first'
            tempdict = {"entry" : False, "id": node_id} #True = Attack
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()


            #If we have an action from each of the nodes,
            #its time for the second round and we send our response_vector vector to the other nodes
            print "Amount of 'None's: " + str(response_vector.count(None))
            if response_vector.count(None)==0:

                #store our own list in the all list
                all_vectors[node_id -1] = response_vector
                print "Retreat response_vector 2: " + str(response_vector)
                print "Retreat all_vectors" + str(all_vectors)

                path = '/vote/receive/second'
                tempdict = {"entry" : response_vector, "id": node_id} #True = Attack
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()

            return "Retreating"
        except Exception as e:
            print e
        return False


    @app.post('/vote/byzantine')
    def is_byzantine():
        global status, amount_of_vessels
        status= 3

        #print str(amount_of_vessels)#debug

        #creates a list of the responses for all nodes (including itself for simplicity since
        # it makes the list the right length for the byzantine_propagate method)
        byzantine_response = compute_byzantine_vote_round1(amount_of_vessels, amount_of_vessels, tie_breaker_value)
        print "Byzantine responses: " + str(byzantine_response) #debug

        #store our own value
        response_vector[int(node_id)-1]= byzantine_response[int(node_id)-1]
        print "Byzantine Response vector: " + str(response_vector)

        #Propagate the update to all the other vessels via the byzantine_propagate method
        path = '/vote/receive/first'
        tempdict = {"entry" : False, "id": node_id} #True = Attack
        thread = Thread(target=byzantine_propagate, args=(path, tempdict, 'POST', byzantine_response))
        thread.daemon=True
        thread.start()

        #If we have an action from each of the nodes,its time for the second round
        #and time to generate our byzantine response vectors
        if response_vector.count(None)==0:

            #generate byzantine votes and add our newly generated vector to all_vectors
            byzantine_vectors=compute_byzantine_vote_round2(amount_of_vessels ,amount_of_vessels,tie_breaker_value)
            all_vectors[node_id-1] = byzantine_vectors[node_id-1]

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

        size = len(all_vectors)
        final_result_vector = []
        final_result = ""

        #for simplicity
        for i in range(0,size):
            final_result_vector.append(None)

        #all_vectors[0]= waht vessel 1 recievd from all vessels (including itself)
        #all_vectors[0][2]=what vessel 3 said to vessel 1 on the first round
        #for each(x in 4)

        print "length of all vectors: "+str(size)

        if all_vectors.count(None)==0:
            #size = len(all_vectors)
            for inside_index in range(0, size):
                counter = 0
                for outside_index in range(0, size):
                    if inside_index != outside_index: #ignore the "diagonal"

                        if all_vectors[outside_index][inside_index]:
                            counter = counter + 1
                            print "inside_index: "+str(inside_index) + " outside_index: " +str(outside_index) +" counter: "+ str(counter)
                        else:
                            counter = counter - 1
                            print "inside_index: "+str(inside_index) + " outside_index: " +str(outside_index) +" counter: "+ str(counter)

                print "count of inside_index: " +str(inside_index) + " is: "+ str(counter)
                if counter > 0:
                    final_result_vector[inside_index] = True
                elif counter < 0:
                    final_result_vector[inside_index] = False
                else:
                    final_result_vector[inside_index] = tie_breaker_value

        return str(all_vectors) + "\n" + str(final_result_vector)
        """
            #For pretty print and final coun

            finalcounter = 0
            for final_index in range(0, size):

                if final_result_vector[final_index]:
                    finalcounter = finalcounter + 1

                else:
                    finalcounter = finalcounter - 1

            if finalcounter > 0:
                final_result = "Everyone is Attacking"

            elif finalcounter < 0:
                final_result = "Everyone is Waiting"

            else:
                if tie_breaker_value:
                    final_result = "Everyone is Attacking"

                else:
                    final_result = "Everyone is Waiting"

            return str(final_result_vector) + "/n" + str(all_vectors) + "/n" + final_result

        else:
            return "Not every one has voted"
            """


    @app.post('/vote/receive/first')
    def receive_from_other():
        global response_vector, status,all_vectors
        try:
            entry = request.forms.get("entry")
            id = request.forms.get("id")
            response_vector[int(id)-1]= entry== 'True'#string comparision since entry is a string

            print "Receive first's response_vector: " + str(response_vector) #debugg
            print "From: " + str(id)

            #If we have an action from each of the nodes,
            #its time for the second round
            #but we need to check the status aswell to se if this node is a byzantine (since byzantines does byzantine stuff)
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

                    #store the received list in the all-list list

                    byzantine_vectors=compute_byzantine_vote_round2(amount_of_vessels,amount_of_vessels,tie_breaker_value)
                    all_vectors[node_id -1] = byzantine_vectors[node_id -1]

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
            entry = request.forms.getall("entry")
            id = request.forms.get("id")
            print "Entry in receive second: " + str(entry)
            print "From in receive second: " + str(id)


            #need to clean up the entry since request.form.getall returns the
            #list of bools as a list of strings
            for index in range(0, len(entry)):
                entry[index]= entry[index]=='True'

            #add the cleaned entry to the list of all vectors
            all_vectors[int(id)-1]= entry

            print "All vectors: " + str(all_vectors) #debugg

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
