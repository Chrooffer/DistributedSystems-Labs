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
import ast
from threading import Thread
from threading import Timer
from time import sleep
import copy
from random import *

from bottle import Bottle, run, request, template
import requests



# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()
    board = {0:"nothing"}
    priority = randint(1,10000)
    leader_id = None

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
    # ------------------------------------------------------------------------------------------------------
        #new_post_number checks for the first avaviable key and returns it
    def new_post_number():
        i = 0
        while board.has_key(i):
            i += 1
        return i

    def check_leader():
        global node_id
        success = False
        try:
            #if we don't have a leader start an election
            if leader_id == None:
                #dedicated path for the election and the next node's ip
                path = '/election/0/'
                ip = '10.1.0.{}'.format(str((node_id % amount_of_nodes)+1))
                dict = {"entry": str({node_id: priority}), "starter_id":node_id}
                #print (dict["entry"]) #debugtool

                return contact_vessel(ip, path, dict, 'POST')
                #thread = Thread(target=contact_vessel, args=(ip, path, dict,'POST') )
                #thread.daemon=True
                #thread.start()
                #res = requests.post('http://{}{}'.format(node_id, path), data=dictus)

                #waiting_counter = 0

            success = True
        except Exception as e:
            print e
        return success

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

    @app.get('/board')
    def get_board():
        global board, node_id
        #print ("in /board (get)") #debugtool
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        '''Adds a new element to the board
        Called directly when a user is doing a POST request on /board'''
        global board, node_id
        try:
    	    #print ("in /board (post)") #debugtool
            check_leader()

            print(leader_id) #debugtool
            #Calls on help function
            nrPosts = new_post_number()

            #Get the entry and add it to local board
            new_element = request.forms.get('entry')
            #add_new_element_to_store(nrPosts, new_element)

            #we create a timer for the actual message to the leader and let it wait in the background
            timer = Timer(2, client_add_received_HELPER, [new_element])
            timer.daemon=True
            timer.start()


            return {'id':node_id,'entry':new_element}
        except Exception as e:
            print e
        return False

    # ------------------------------------------------------------------------------------------------------
    def client_add_received_HELPER(element):
        try:
            #dynamic time adding
            if leader_id == None:
                threader = Timer(1, client_add_received_HELPER, [element])
                threader.daemon=True
                threader.start()
            else:
                path = '/leader'
                ip = '10.1.0.{}'.format(str(leader_id))
                tempdict = {"entry": str(element)}
                #print (dict["entry"]) #debugtool
                thread = Thread(target=contact_vessel, args=(ip,path,tempdict,'POST') )
                thread.daemon=True
                thread.start()
                return True
        except Exception as e:
            print e
        return False

    # ------------------------------------------------------------------------------------------------------
    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
    	global board, node_id
    	try:
            #print ("in /board/<element_id:int>/") #debugtool

            #Get the new element, and the comand (optional)
            new_element = request.forms.get("entry")
            action = request.forms.get("delete")

            #Propagate it to the leader
            leader_ip = '10.1.0.{}'.format(leader_id)
            path = '/leader/'+ str(action) +'/' + str(element_id) +'/'
            tempdict = {"entry" : new_element}

            thread = Thread(target=contact_vessel, args=(leader_ip,path,tempdict,'POST') )
            thread.daemon=True
            thread.start()
            return {'id':element_id,'entry':new_element}
    	except Exception as e:
            print e
            return False

    # ------------------------------------------------------------------------------------------------------
    @app.post('/propagate/<element_id:int>')
    def propagation_received(element_id):
        try:
            elementToAdd = request.forms.get("entry")
            add_new_element_to_store(element_id, elementToAdd)
            return {'id':element_id,'entry':elementToAdd}
        except Exception as e:
            print e
            return False

    # ------------------------------------------------------------------------------------------------------
    @app.post('/propagate/<action:int>/<element_id:int>')
    def propagation_action_received(action, element_id):
        #print ("in /propagate/<action>/<element_id>") #debugtool
        try:
            elementToModify = request.forms.get("entry")
            #print(element_id) #debugtool
            #print(elementToModify) #debugtool

            #Check to see the comand of the action
            #action is either 0 for modify or 1 for delete
            if (action == 0):
                modify_element_in_store(element_id,elementToModify)
            else:
                delete_element_from_store(element_id)

            return {'id':element_id,'entry':elementToModify}

        except Exception as e:
            print e
            return False
    #-------------------------------------------------------------------------------------------------------
    @app.post('/election/<action:int>/')
    def start_election(action):
        global amount_of_nodes
        global leader_id
        print ("in election/action/")#debugtool
        #payload is a dict and is formated: {"entry":{0:1000, 1:23,...}, "starter_id": <int>}
        try:
            starter_id= request.forms.get("starter_id")
            print(str(starter_id))#debugtool

            #ast.literal_eval is a safer verision of eval
            candidates = ast.literal_eval(request.forms.get('entry'))
            print(candidates)#debugtool
            print("!!!!!Above is Proof of dictionary!!!!!")
            print(amount_of_nodes)
            print(node_id)

            #if we have not added our id and priority to the candidates, then do so and propegate to the next node
            if not (node_id in candidates):
                #the path
                path = '/election/0/'

                #update candidates with own id and priority
                candidates.update({node_id: priority})
                print(candidates)#debugtool

                #create the new dictonary (payload)
                tmpdict = {"entry": str(candidates), "starter_id":starter_id}

                #send to next node
                next_ip = '10.1.0.{}'.format(str((node_id % amount_of_nodes)+1))
                thread = Thread(target=contact_vessel, args=(next_ip,path,tmpdict,'POST') )
                thread.daemon=True
                thread.start()
            else:
                print("before if")#debugtool
                #If this is not true, we have passed stage 1, and is therefore done

                print (leader_id)
                if leader_id == None:
                    print("passed if")#debugtool
                    highest_key = 0
                    highest_value = 0

                    for key,value in candidates.items():
                        if value > highest_value:
                            highest_key = key
                            highest_value = value
                    print("before leader_id assignment")#debugtool
                    leader_id = highest_key
                    print("after leader_id assignment")#debugtool
                    print(leader_id)

                    path = '/election/1/'
                    next_ip = '10.1.0.{}'.format(str((node_id % amount_of_nodes)+1))
                    tmpdict = {"entry": str(candidates), "starter_id":starter_id}
                    thread = Thread(target=contact_vessel, args=(next_ip,path,tmpdict,'POST') )
                    thread.daemon=True
                    thread.start()

                #if node_id == starter_id election is over

            return {'id':node_id,'entry':candidates}
        except Exception as e:
            print e
            return False

    #Only for making a Post
    @app.post('/leader')
    def propagate_post_to_leader():

        global board, node_id
        try:
            #Redundancy check, just in case
            #print ("in /board (post)") #debugtool

            #Calls on help function
            nrPosts = new_post_number()

            #Get the entry and add it to local board
            new_element = request.forms.get('entry')
            add_new_element_to_store(nrPosts, new_element)

            #Propagate the update to all the other vessels
            path = '/propagate/'+ str(nrPosts)
            tempdict = {"entry" : new_element}
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()
            return {'id':nrPosts,'entry':new_element}


        except Exception as e:
            print e
            return False

    #Only for Modify and Delete, depending on Action value
    @app.post('/leader/<action:int>/<element_id:int>/')
    def propagate_action_to_leader(action, element_id):
        global board, node_id
    	try:
            #print ("in /board/<element_id:int>/") #debugtool
            #Get the new element, and the comand (optional)
            new_element = request.forms.get("entry")
            #Check if it has a comand
            #Do the change localy
            if (action == 1):
                delete_element_from_store(element_id)
            else:
                modify_element_in_store(element_id, new_element)

            print(action)
            #Propagate it to the other vessels
            path = '/propagate/'+ str(action) +'/' + str(element_id)
            tempdict = {"entry" : new_element}
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()

            return {'id':element_id,'entry':new_element}

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
        global vessel_list, node_id, app, amount_of_nodes

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        amount_of_nodes = max(0,args.nbv-1) #for the election, it is required to know the amount of nodes
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
