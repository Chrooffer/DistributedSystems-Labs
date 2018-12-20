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
from threading import Lock
import copy
from bottle import Bottle, run, request, template
import requests
from operator import itemgetter


# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()
    board = {}
    logical_clock = 0
    #[{"action": int, "element_id": int,"element_entry": str, "clock_value": int, "sender_id": int}, {...} ...]
    stored_comands = []

    #used to measure and store the time it takes for consistency
    is_first_message = True
    time_of_first_message =0

    #This implementation requires the use of a lock inorder to block the incommming posts during
    #the sorting part, since the incommming posts can (and will) change the stored_comands list (since it's global
    #and thus accessable by all threads) during the sorting part and thus poentially making the
    #stored_comands unsorted. The lock is also used when incrementing the logical_clock as a
    #safety precaution (since it's also global and thus can cause problems with the stored_comands).
    lock = Lock()

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Should nopt be given to the student
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(entry_sequence, element, board, is_propagated_call=False):
        global node_id
        success = False
        try:
            #print ("in add_new_element_to_store")#debugtool

            #if the key exists we can't add a new entry to that key (since that is an "modify action")
            if not board.has_key(entry_sequence):
                board.update({entry_sequence: element})

            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_sequence, modified_element, board, is_propagated_call = False):
        global node_id
        success = False
        try:
            #print ("in modify_element_in_store") #debugtool

            #Check if entry_sequence exists, if it does, modify it, otherwise don't do anything
            #print str(board.has_key(entry_sequence))
            if board.has_key(entry_sequence):
                board[entry_sequence]=modified_element

            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, board, is_propagated_call = False):
        global node_id
        success = False
        try:
            #print ("in delete_element_from_store")#debugtool
            del board[entry_sequence]
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # HELP FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    #new_post_number checks for the first avaviable key and returns it
    def new_post_number():
        i = 0
        while board.has_key(i):
            i += 1
        return i

    #method sorts the stored_comands, first by their sender_id and the with their clock_value
    #this kind of sorting makes it that the lowest clock_value appear first and if several
    #nodes had the same clock_value, the lowest id gets priority. The sorting method utilizes
    #the stable sorting property, which pythons built in sort function has
    def sort_stored_comands():
        global stored_comands

        #create tmp_comands
        tmp_comands = stored_comands

        #sort by sender id
        tmp_comands = sorted(tmp_comands, key = itemgetter('sender_id'))

        #sort by clock_value
        tmp_comands = sorted(tmp_comands, key = itemgetter('clock_value'))

        #update the stored_comands
        stored_comands = tmp_comands
        return True

    def apply_stored_comands():
        #We apply all stored actions to the starting board, if every node has the same list
        #of sorted comands and applies them to the same starting board and in the same
        #order, then their boards must be the same!
        tempdict = {}
        for comand in stored_comands:
            if comand.has_key("action") and comand.get("action") == 0:
                #code for modify is 0
                modify_element_in_store(comand.get("element_id"),comand.get("element_entry"), tempdict)

            elif comand.has_key("action") and comand.get("action") == 1:
                #code for delete is 1
                delete_element_from_store(comand.get("element_id"), tempdict)

            elif comand.has_key("action") and comand.get("action") == None:
                #code for adding a new elem is None (since adding doesnt have a action variable)
                add_new_element_to_store(comand.get("element_id"),comand.get("element_entry"), tempdict)

            else:
                print"A faulty comand was entered" + str(comand)

        return tempdict

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
        global vessel_list, node_id, logical_clock

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself

                #print payload["logical_clock"]#debugtool
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
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=board.iteritems(), members_name_string='Group 97')

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
        global board, node_id, logical_clock, is_first_message, time_of_first_message
        try:
            #start time measurement
            if is_first_message:
                is_first_message = False
                time_of_first_message = time.time()

            #change the logical clock (inside the lock)
            lock.acquire(True)
            logical_clock = logical_clock +1

            #Calls on help function
            nrPosts = new_post_number()

            #Get the entry and add it to local board
            new_element = request.forms.get('entry')
            add_new_element_to_store(nrPosts, new_element, board)

            #Add it to the stored comands, since when we re-create the board, we want to include the ones we sent awswell
            stored_comands.append({"action": None, "element_id": nrPosts,"element_entry": new_element, "clock_value": int(logical_clock), "sender_id": int(node_id)})

            #Propagate the update to all the other vessels
            path = '/board/'+ str(nrPosts) +'/'
            tempdict = {"entry" : new_element, "logical_clock": logical_clock, "sender_id": node_id}
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()

            #release lock
            lock.release()

            print "Seconds since first message: " +str(time.time() - time_of_first_message)
            return {'id':nrPosts,'entry':new_element}
        except Exception as e:
            print e
        return False

    # ------------------------------------------------------------------------------------------------------
    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global board, node_id, logical_clock, is_first_message, time_of_first_message
        try:
            #start time measurement
            if is_first_message:
                is_first_message = False
                time_of_first_message = time.time()

            #print ("in /board/<element_id:int>/") #debugtool

            #Get the new element, and the comand (possible that it's equal to None)
            new_element = request.forms.get("entry")
            action = request.forms.get("delete")
            clock_value = request.forms.get("logical_clock")
            sender_id = request.forms.get("sender_id")

            #Check if it has a comand
            if (action != None):

                #Do the change localy
                if (action == '1'):
                    delete_element_from_store(element_id, board)
                else:
                    modify_element_in_store(element_id, new_element,board)

                #change the logical clock (inside of the lock)
                lock.acquire(True)
                logical_clock = logical_clock +1

                #Add it to the stored comands, since when we re-create the board, we want to include the ones we sent awswell
                stored_comands.append({"action": int(action), "element_id": element_id,"element_entry": new_element, "clock_value": int(logical_clock), "sender_id": int(node_id)})

                #Propagate it to the other vessels
                path = '/propagate/'+ str(action) +'/' + str(element_id) +'/'
                tempdict = {"entry" : new_element, "logical_clock": logical_clock, "sender_id": node_id}
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()

                #release the lock
                lock.release()
                print "Seconds since first message: " +str(time.time() - time_of_first_message)
            else:

                #grab the lock
                lock.acquire(True)

                #print "Unsorted"
                #for x in stored_comands: #debug, for-loop prints the stored_comands
                #    print x

                #insert comand to the storage
                stored_comands.append({"action": None, "element_id": element_id,"element_entry": new_element, "clock_value": int(clock_value), "sender_id": int(sender_id)})

                #increase our logical clock
                logical_clock = max(int(logical_clock),int(clock_value)) +1

                #sort the comands
                sort_stored_comands()

                #print "Sorted"
                #for x in stored_comands: #debug, for-loop prints the stored_comands
                #    print x

                #print str(board) #debug before applying stored comands

                #update the board
                board = apply_stored_comands()

                #print str(board) #debug after applying stored comands

                #release the lock
                lock.release()

                print "Seconds since first message: " +str(time.time() - time_of_first_message)

            return {'id':element_id,'entry':new_element}
        except Exception as e:
            print e
            return False

    @app.post('/propagate/<action:int>/<element_id:int>/')
    def propagation_received(action, element_id):
        global logical_clock, board
        #print ("in /propagate/<action>/<element_id>") #debugtool
        try:
            elementToModify = request.forms.get("entry")
            clock_value = request.forms.get("logical_clock")
            sender_id = request.forms.get("sender_id")

            #grab the lock
            lock.acquire(True)

            #for x in stored_comands: #debug, for-loop prints the stored_comands
            #    print x

            #insert comand to the storage
            stored_comands.append({"action": int(action), "element_id": element_id,"element_entry": elementToModify, "clock_value": int(clock_value), "sender_id": int(sender_id)})

            #increase our logical clock
            logical_clock = max(int(logical_clock),int(clock_value)) +1

            #for x in stored_comands: #debug, for-loop prints the stored_comands
            #    print x

            #sort the comands
            sort_stored_comands()

            #print str(board) #debug before applying stored comands

            #update the board
            board = apply_stored_comands()

            #print str(board) #debug after applying stored comands

            #release the lock
            lock.release()

            print "Seconds since first message: " + str(time.time() - time_of_first_message)
            return {'id':element_id,'entry':elementToModify}
        except Exception as e:
            print e
            return False
            #action is either 0 for modify or 1 for delete

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post Give it to the students
    # Execute the code
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
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
