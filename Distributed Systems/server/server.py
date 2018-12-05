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

    def create_election():
        global node_id
        success = False
        try:
            #only if we don't have a leader start an election

            #when we create an election we reset the leader
            leader_id = None

            print("Createing an election")#debug tool

            #path for the election and the next node's ip
            path = '/election'
            ip = '10.1.0.{}'.format(str((node_id % amount_of_nodes)+1))

            #the payload dictonary
            dict = {"entry": str({node_id: priority})}

            #return contact_vessel(ip, path, dict, 'POST')
            thread = Thread(target=contact_vessel, args=(ip, path, dict,'POST') )
            thread.daemon=True
            thread.start()

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
            create_election()
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
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=board.iteritems(), members_name_string='Group 97', leader_id_string = str(leader_id), random_number_string= str(priority))

    @app.get('/board')
    def get_board():
        global board, node_id
        #print ("in /board (get)") #debugtool
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=board.iteritems())
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        '''Adds a new element to the board
        Called directly when a user is doing a POST request on /board'''
        global board, node_id
        try:
            #if this node doesn't have a leader, create an election
            if leader_id == None:
                create_election()

            #get the entry that is going to be added to the board
            new_element = request.forms.get('entry')

            #we create a timer (seconds) for the actual message to the leader and let it wait in the background
            #for the possible election. When the time is up, the help method is called with the arg; new_element
            timer = Timer(0.1, client_add_received_HELPER, [new_element, 0])
            timer.daemon=True
            timer.start()

            #time.sleep(5)#debugtool (to check if the helper is running concurently and delays properly)

            return {'entry':new_element}
        except Exception as e:
            print e
        return False

    # ------------------------------------------------------------------------------------------------------
    def client_add_received_HELPER(element, itterations):
        try:
            #dynamic time adding if the leader is unknown (the election is still ongoing)
            if leader_id == None:
                if itterations <10:
                    print("Waiting for election to finish")#debugtool
                    threader = Timer(3, client_add_received_HELPER, [element, (itterations+1)])
                    threader.daemon=True
                    threader.start()
                else:
                    #something went wrong with the election, make a new election
                    create_election()
            else:
                #if we know the leader we send the message to it
                path = '/leader'
                leader_ip = '10.1.0.{}'.format(str(leader_id))
                tempdict = {"entry": str(element)}

                #propegate to leader
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
            #if this node doesn't have a leader, create an election
            if leader_id == None:
                create_election()

            #get the new element, and the action (optional)
            new_element = request.forms.get("entry")
            action = request.forms.get("delete")

            #we create a timer (seconds) for the actual message to the leader and let it wait in the background
            #for the possible election. When the time is up, the help method is called with the arg; new_element
            timer = Timer(0.1, client_action_received_HELPER, [new_element, element_id, action, 0])
            timer.daemon=True
            timer.start()

            #time.sleep(5)#debugtool (to check if the helper is running concurently and delays properly)

            return {'id':element_id,'entry':new_element}
        except Exception as e:
            print e
            return False
    # ------------------------------------------------------------------------------------------------------
    #helpfunction for posts made to "/board/<element_id:int>/"
    def client_action_received_HELPER(element, element_id, action, itterations):
        try:
            #dynamic time adding if the leader is unknown (the election is still ongoing)
            if leader_id == None:
                if itterations <10:
                    print("Waiting for election to finish")#debugtool
                    threader = Timer(3, client_add_received_HELPER, [element, element_id, action, (itterations+1)])
                    threader.daemon=True
                    threader.start()
                else:
                    #something went wrong with the election, make a new election
                    create_election()
            else:
                #if we know the leader send the message to it
                leader_ip = '10.1.0.{}'.format(leader_id)
                path = '/leader/'+ str(action) +'/' + str(element_id) +'/'
                tempdict = {"entry" : element}

                #propagate it to the leader
                thread = Thread(target=contact_vessel, args=(leader_ip,path,tempdict,'POST') )
                thread.daemon=True
                thread.start()
                return True
        except Exception as e:
            print e
        return False
    # ------------------------------------------------------------------------------------------------------
    @app.post('/propagate/<element_id:int>')
    def propagation_received(element_id):
        try:
            #add element to board
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
    @app.post('/election')
    def start_election():
        global amount_of_nodes
        global leader_id
        print ("In election cycle")#debugtool
        #payload is a dict and is formated: {"entry":str({0:1000, 1:23,...})}
        try:
            #the dictionary containing the candidates are sent as a string and thus
            #needs to be converted into a dict again, here via the use of a safe version of
            #the built in "eval" function (ast.literal_eval only accepts a small subset
            #of Python literals namely; strings, numbers, tuples, lists, dicts, booleans)
            #inorder to stop code injections from executing
            candidates = ast.literal_eval(request.forms.get('entry'))

            #if we have not added our id and priority to the candidates, then do so and propegate to the next node
            #since we have not yet added ourselfs to the candidates we must be on the first itteration of the election
            if not (node_id in candidates):
                #Clear the current leader, (since we are electing a new one)
                leader_id = None

                #the path for the continuation
                path = '/election'

                #update candidates with own id and priority
                candidates.update({node_id: priority})
                print(candidates)#debugtool

                #create the new dictonary (payload)
                tmpdict = {"entry": str(candidates)}

                #send to next node
                next_ip = '10.1.0.{}'.format(str((node_id % amount_of_nodes)+1))
                thread = Thread(target=contact_vessel, args=(next_ip,path,tmpdict,'POST') )
                thread.daemon=True
                thread.start()
            else:

                print ("The leader's ID (before assignment) is: " + str(leader_id))#debugtool
                #If this is not true, we have passed stage 1, and is therefore
                # done (this works because leader_id was cleared in the first loop of
                # the election process)
                if leader_id == None:
                    highest_key = 0
                    highest_value = 0

                    #Check to see which id has the highest value, let the corresponding id become the leader
                    for key,value in candidates.items():
                        if value > highest_value:
                            highest_key = key
                            highest_value = value
                    leader_id = highest_key
                    print ("The leader's ID is: " + str(leader_id))#debugtool

                    #send to the next node
                    path = '/election'
                    next_ip = '10.1.0.{}'.format(str((node_id % amount_of_nodes)+1))
                    tmpdict = {"entry": str(candidates)}
                    thread = Thread(target=contact_vessel, args=(next_ip,path,tmpdict,'POST') )
                    thread.daemon=True
                    thread.start()

                else:
                    #if we already knew our leader before checking the candidates, we must
                    #already have done so and so has every one else, thus we can terminate the election
                    print ("End election, winner: " + str(leader_id))
            return {'id':node_id,'entry':candidates}
        except Exception as e:
            print e
            return False

    #Leader handeling of addnig new entries to the board
    @app.post('/leader')
    def propagate_post_to_leader():

        global board, node_id
        try:

            #Calls on help function to generate the new element_id
            nrPosts = new_post_number()

            #Get the entry and add it to local board
            new_element = request.forms.get('entry')
            add_new_element_to_store(nrPosts, new_element)

            #propagate the update to all the other vessels
            path = '/propagate/'+ str(nrPosts)
            tempdict = {"entry" : new_element}
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()
            return {'id':nrPosts,'entry':new_element}


        except Exception as e:
            print e
            return False

    #Leader handeling of Modify and Delete, depending on Action value
    @app.post('/leader/<action:int>/<element_id:int>/')
    def propagate_action_to_leader(action, element_id):
        global board, node_id
        try:


            #Get the new element, and the comand (optional)
            new_element = request.forms.get("entry")

            #Check which comand and change it localy
            if (action == 1):
                delete_element_from_store(element_id)
            else:
                modify_element_in_store(element_id, new_element)

            #print(action)#debugtool

            #propagate it to the other vessels
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
