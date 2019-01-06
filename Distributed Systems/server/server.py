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
    responce_vector=[]
    all_vectors=[]
    tie_breaker = True #True for attack to win a tie, False for retreat to win a tie


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
        #print ("in propagate_to_vessels")#debugtool
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


    @app.post('/vote/attack')
    def is_attacking():
        global status,node_id
        try:
            status= 1
            responce_vector[int(node_id)-1]= True
            print str(responce_vector) #debugg

            #Propagate the update to all the other vessels
            path = '/vote/receive/first'
            tempdict = {"entry" : True, "id": node_id} #True = Attack
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
            responce_vector[int(node_id)-1]= False
            print str(responce_vector) #debugg

            #Propagate the update to all the other vessels
            path = '/vote/receive/first'
            tempdict = {"entry" : False, "id": node_id} #True = Attack
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

        #creates a list of the responces for all nodes (including itself)
        byzantine_responce = compute_byzantine_vote_round1(amount_of_vessels,1,tie_breaker)
        print "Byzantine recponces: " + str(byzantine_responce) #debug

        #store our own value
        responce_vector[int(node_id)-1]= byzantine_responce[int(node_id)-1]
        print "Responce vector: " + str(responce_vector)

        #Propagate the update to all the other vessels via the byzantine_propagate method
        path = '/vote/receive/first'
        tempdict = {"entry" : False, "id": node_id} #True = Attack
        thread = Thread(target=byzantine_propagate, args=(path,tempdict,'POST',byzantine_responce))
        thread.daemon=True
        thread.start()

        return "Byzantineing"


    @app.get('/vote/result')
    def vote_result():
        return str([])


    @app.post('/vote/receive/first')
    def receive_from_other():
        global responce_vector
        try:
            entry = request.forms.get("entry")
            id = request.forms.get("id")
            responce_vector[int(id)-1]= entry== 'True'#string comparision since entry is a string

            print str(responce_vector) #debugg

            return {"entry":entry, "id":id}
        except Exception as e:
            print e
        return False


    @app.post('/vote/receive/second')
    def receive_from_other_all():
        global responce_vector
        try:
            entry = request.forms.get("entry")
            id = request.forms.get("id")

            #add the entry to the list with all vectors
            all_vectors[int(id)-1]= entry

            print str(all_vectors) #debugg

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
        global vessel_list, node_id, app,amount_of_vessels,responce_vector, all_vectors

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        amount_of_vessels = args.nbv -1

        for i in range(1, args.nbv): #fills the vectors with "None" as placeholder values
            responce_vector.append(None)
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
