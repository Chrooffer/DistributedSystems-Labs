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
    board = {0:"nothing"}

    nrPosts = 0

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Should nopt be given to the student
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            print ("in add_new_element_to_store")
            board.update({entry_sequence: element})
            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            print ("in modify_element_in_store")
            #copy.deepcopy(board[, memo])
            #Could potentially just be the same code as add_new_element_to_store, but doing this for concurrency
            board.update({entry_sequence: element})
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            print ("in delete_element_from_store")
            del board[entry_sequence]
            success = True
        except Exception as e:
            print e
        return success

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
        #req = POST in the case of Propagate to vessel
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                print("in contact vessel POST")
                res = requests.post('http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                print ("in contact_vessel GET")
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload, req):
        print ("in propagate_to_vessels")
        #req = POST in the case of "client_add_received"
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
        print ("in / (route)")
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()), members_name_string='Group 97')

    @app.get('/board')
    def get_board():
        global board, node_id
        print board
        print ("in /board (get)")
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        '''Adds a new element to the board
        Called directly when a user is doing a POST request on /board'''
        global board, node_id , nrPosts
        try:
    	    print ("in /board (post)")
            #new_entry = request.forms.get('id')
            #Error: 404 Not Found
            #Sorry, the requested URL <tt> %#039;/board/5&#039; </tt> caused an error SOLVED BY ADDING "/" AT THE END
            nrPosts = new_post_number()
            new_element = request.forms.get('entry')
            print (new_element)
    	    ##new_element = request.forms.get('value')
            add_new_element_to_store(nrPosts, new_element)

            ##add_new_element_to_store(element_id, new_element) -> error global name 'element_id' is not defined
            path = '/board/'+ str(nrPosts) +'/'
            tempdict = {"entry" : new_element}
     	    thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )#Todo (lab2?) change none to a unused id for the new post
    	    thread.daemon=True
    	    thread.start()

            # you should create the thread as a deamon
            return {'id':element_id,'entry':new_element}
        except Exception as e:
            print e
        return False


    # ------------------------------------------------------------------------------------------------------
    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        #begin todo
    	global board, node_id
    	try:
            print ("in /board/<element_id:int>/")
            new_element = request.forms.get("entry")
            print(new_element)

            action = request.forms.get('delete')
            print(action)
            #new_element = request.forms.get('{{board_element}}')
            if (action == '1') or (action == '0'):
                if (action == '1'):
                    delete_element_from_store(element_id)
                else:
                    modify_element_in_store(element_id, new_element)
                path = '/propagate/'+ action +'/' + str(element_id) +'/'
                tempdict = {"entry" : new_element}
                thread = Thread(target=propagate_to_vessels, args=(path,tempdict,'POST') )
                thread.daemon=True
                thread.start()
            else:
                add_new_element_to_store(element_id, new_element)

            return {'id':element_id,'entry':new_element}
            #return True

        ## this exception breaks the simulation, dunno why
    	except Exception as e:
            print e
            return False
        #return True
        #pass
        #end todo

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        print ("in /propagate/<action>/<element_id>")
        # todo
        try:
            elementToModify = request.forms.get("entry")#correct form
            if action == 0:
                modify_element_in_store(element_id,elementToModify)
            elif action == 1:
                delete_element_from_store(element_id)
            return True
        except Exception as e:
            print e
            return False
	    #action is either 0 for modify or 1 for delete
        #pass


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
        # We need to write the other vessels IP, based on the knowledge of their number
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
