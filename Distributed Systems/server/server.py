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
import copy
from bottle import Bottle, run, request, template
import requests
from operator import itemgetter


# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()
    board = {0:"nothing"}
    logical_clock = 0
    #[{"action": int, "element_id": int,"element_entry": str, "clock_value": int, "sender_id": int}, {...} ...]
    stored_comands = []

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

    def sort_stored_comands():
        global stored_comands
        tmp_comands = sorted(tmp_comands, key = itemgetter('sender_id')) #works due to stable sorting property of python
        tmp_comands = sorted(stored_comands, key = itemgetter('clock_value'))
        stored_comands = tmp_comands
        return True

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
                #sending a message to a node is considered a new event, thus increment by 1
                logical_clock = logical_clock +1
                payload["logical_clock"] = logical_clock

                print (payload["logical_clock"])#debugtool
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
        global board, node_id
        try:
            #print ("in /board (post)") #debugtool

            #Calls on help function
            nrPosts = new_post_number()

            #Get the entry and add it to local board
            new_element = request.forms.get('entry')
            add_new_element_to_store(nrPosts, new_element)

            print "node_id: " + str(node_id)
            #Propagate the update to all the other vessels
            path = '/board/'+ str(nrPosts) +'/'
            tempdict = {"entry" : new_element, "logical_clock": logical_clock, "sender_id": node_id}
            thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
            thread.daemon=True
            thread.start()

            return {'id':nrPosts,'entry':new_element}
        except Exception as e:
            print e
        return False


    # ------------------------------------------------------------------------------------------------------
    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global board, node_id, logical_clock
        try:
            #print ("in /board/<element_id:int>/") #debugtool

            #Get the new element, and the comand (optional)
            new_element = request.forms.get("entry")
            action = request.forms.get("delete")
            clock_value = request.forms.get("logical_clock")
            sender_id = request.forms.get("sender_id")
            print "sender_id: " + str(sender_id)#debug
            #Check if it has a comand
            if (action != None):

                #Do the change localy
                if (action == '1'):
                    delete_element_from_store(element_id)
                else:
                    modify_element_in_store(element_id, new_element)

                #Propagate it to the other vessels
                path = '/propagate/'+ str(action) +'/' + str(element_id) +'/'
                tempdict = {"entry" : new_element, "logical_clock": logical_clock, "sender_id": node_id}
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()
            else:
                #inser to comand storage at index 0 (pushing the rest of the indexes "forward")
                stored_comands.append({"action": None, "element_id": element_id,"element_entry": new_element, "clock_value": clock_value, "sender_id": sender_id})

                #increase our logical clock
                #logical_clock = int(max(logical_clock,clock_value) )+1

                for x in stored_comands: #debug, for-loop prints the stored_comands
                    print x

                sort_stored_comands()
                for x in stored_comands: #debug, for-loop prints the stored_comands
                    print x



                add_new_element_to_store(element_id, new_element)

            return {'id':element_id,'entry':new_element}
        except Exception as e:
            print e
            return False

    @app.post('/propagate/<action:int>/<element_id:int>/')
    def propagation_received(action, element_id):
        global logical_clock
        #print ("in /propagate/<action>/<element_id>") #debugtool
        try:
            elementToModify = request.forms.get("entry")
            clock_value = request.forms.get("logical_clock")
            sender_id = request.forms.get("sender_id")
            #print(element_id) #debugtool
            #print(elementToModify) #debugtool

            #inser to comand storage at index 0 (pushing the rest of the indexes "forward")
            stored_comands.append({"action": action, "element_id": element_id,"element_entry": elementToModify, "clock_value": clock_value, "sender_id": sender_id})

            #increase our logical clock
            #logical_clock = int(max(logical_clock,clock_value) )+1

            #Check to see the comand of the action
            if action == 0:
                modify_element_in_store(element_id,elementToModify)
            elif action == 1:
                delete_element_from_store(element_id)

            for x in stored_comands: #debug, for-loop prints the stored_comands
                print x

            sort_stored_comands()
            for x in stored_comands: #debug, for-loop prints the stored_comands
                print x

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
