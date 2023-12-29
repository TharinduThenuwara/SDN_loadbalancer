#!/usr/bin/env python

import requests
from requests.auth import HTTPBasicAuth
import json
import unicodedata
from subprocess import Popen, PIPE
import time
import networkx as nx
from sys import exit

# We request to the ODL controller to get REST data the details from JSON format Method 
def getResponse(url,choice):

	response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin'))

	if(response.ok):
		jData = json.loads(response.content)
		if(choice=="topology"):
			topologyInformation(jData)
		elif(choice=="statistics"):
			getStats(jData)
	else:
		response.raise_for_status()

# We Defined topology informations using JSON file jData
def topologyInformation(data):
	global switch
	global deviceMAC
	global deviceIP
	global hostPorts
	global linkPorts
	global G
	global cost
	for i in data["network-topology"]["topology"]:	
		if "node" in i:
			for j in i["node"]:
				# MAC & IP MAPPING
				# We Defined the Devices MAC addresses and IP addresses from JSON file we got above jData
				if "host-tracker-service:addresses" in j:
					for k in j["host-tracker-service:addresses"]:
						ip = k["ip"].encode('ascii','ignore')
						mac = k["mac"].encode('ascii','ignore')
						deviceMAC[ip] = mac
						deviceIP[mac] = ip

				# SWITCH CONNECTION & PORT MAPPING
				# We Defined the Switch Connection and Port from JSON file we got above jData
				if "host-tracker-service:attachment-points" in j:
					for k in j["host-tracker-service:attachment-points"]:
						mac = k["corresponding-tp"].encode('ascii','ignore')
						mac = mac.split(":",1)[1]
						ip = deviceIP[mac]
						temp = k["tp-id"].encode('ascii','ignore')
						switchID = temp.split(":")
						port = switchID[2]
						hostPorts[ip] = port
						switchID = switchID[0] + ":" + switchID[1]
						switch[ip] = switchID
	# LINK & PORT MAPPING
	# We Defined the Link and Port from JSON file we got above jData
	for i in data["network-topology"]["topology"]:
		if "link" in i:
			for j in i["link"]:
				if "host" not in j['link-id']:
					src = j["link-id"].encode('ascii','ignore').split(":")
					srcPort = src[2]
					dst = j["destination"]["dest-tp"].encode('ascii','ignore').split(":")
					dstPort = dst[2]
					srcToDst = src[1] + "::" + dst[1]
					linkPorts[srcToDst] = srcPort + "::" + dstPort
					G.add_edge((int)(src[1]),(int)(dst[1]))

# We Defined the TOTAL COST get data from jData
def getStats(data):
	print "\nCost Computation....\n"
	global cost
	txRate = 0
	for i in data["node-connector"]:
		tx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["packets"]["transmitted"])
		rx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["packets"]["received"])
		txRate = tx + rx
	# compute the txrate for the initial state
	print "\nTxRate...\n"	
	print txRate

	time.sleep(2)
	# Make a request to a 'stats' endpoint for real time
	response = requests.get(stats, auth=HTTPBasicAuth('admin', 'admin'))
	tempJSON = ""
	if(response.ok):
		tempJSON = json.loads(response.content)

	for i in tempJSON["node-connector"]:
		tx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["packets"]["transmitted"])
		rx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["packets"]["received"])
		# Get the cost for real time traffic (subtracte the initial traffic form it)
		cost = cost + tx + rx - txRate
	print "\ncost\n"
	# cost = cost + txRate
	print cost

def systemCommand(cmd):
	# Popen is used to open a process that runs the specified command in a shell
	terminalProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
	# Communicate with the process and obtain the output and error streams
	terminalOutput, stderr = terminalProcess.communicate()

	print "\n*** Flow Pushed\n"

# Push the flow control rules to the ODL controller
def pushFlowRules(bestPath):
	bestPath = bestPath.split("::")
	for currentNode in range(0, len(bestPath)-1):
		if (currentNode==0):
			inport = hostPorts[h2]
			srcNode = bestPath[currentNode]
			dstNode = bestPath[currentNode+1]
			outport = linkPorts[srcNode + "::" + dstNode]
			outport = outport[0]
		else:
			prevNode = bestPath[currentNode-1]
			print prevNode
			srcNode = bestPath[currentNode]
			print srcNode
			dstNode = bestPath[currentNode+1]
			inport = linkPorts[prevNode + "::" + srcNode]
			inport = inport.split("::")[1]
			outport = linkPorts[srcNode + "::" + dstNode]
			outport = outport.split("::")[0]

		# How traffic should flow (which ports) we can define the src & dest ports and the src & dest addresses 
		# in this example we use "10.0.0.1"-->"10.0.0.4" 
		xmlSrcToDst = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><priority>32767</priority><flow-name>Load Balance 1</flow-name><match><in-port>' + str(inport) +'</in-port><ipv4-destination>10.0.0.1/32</ipv4-destination><ipv4-source>10.0.0.5/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><id>1</id><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(outport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''

		xmlDstToSrc = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><priority>32767</priority><flow-name>Load Balance 2</flow-name><match><in-port>' + str(outport) +'</in-port><ipv4-destination>10.0.0.5/32</ipv4-destination><ipv4-source>10.0.0.1/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><id>2</id><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(inport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
		
		# Programmatically configure flows in an SDN environment source to destination path flow.
		flowURL = "http://10.0.2.15:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[currentNode] +"/table/0/flow/1"

		command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlSrcToDst

		systemCommand(command)
		
		# Programmatically configure flows in an SDN environment destination to source path flow.
		flowURL = "http://10.0.2.15:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[currentNode] +"/table/0/flow/2"

		command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlDstToSrc

		systemCommand(command)

	srcNode = bestPath[-1]
	prevNode = bestPath[-2]
	inport = linkPorts[prevNode + "::" + srcNode]
	inport = inport.split("::")[1]
	outport = hostPorts[h1]

	xmlSrcToDst = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><priority>32767</priority><flow-name>Load Balance 1</flow-name><match><in-port>' + str(inport) +'</in-port><ipv4-destination>10.0.0.1/32</ipv4-destination><ipv4-source>10.0.0.4/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><id>1</id><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(outport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''

	xmlDstToSrc = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><priority>32767</priority><flow-name>Load Balance 2</flow-name><match><in-port>' + str(outport) +'</in-port><ipv4-destination>10.0.0.4/32</ipv4-destination><ipv4-source>10.0.0.1/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><id>2</id><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(inport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''

	# Programmatically configure flows in an SDN environment source to destination path flow.
	flowURL = "http://10.0.2.15/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[-1] +"/table/0/flow/1"

	command = 'curl --user \"admin\":\"admin\" -H \"Accept: application/xml\" -H \"Content-type: application/xml\" -X PUT ' + flowURL + ' -d ' + xmlSrcToDst

	systemCommand(command)

	# Programmatically configure flows in an SDN environment destination to source path flow.
	flowURL = "http://10.0.2.15:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[-1] +"/table/0/flow/2"

	command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlDstToSrc

	systemCommand(command)


# Take the input as integer which represent the last number of the ip addresses (10.0.0.X) X is the input
# Main

# Stores H1 and H2 from user
global h1,h2#,h3

h1 = ""
h2 = ""

print "Enter Host 1"
h1 = int(input())
print "\nEnter Host 2"
h2 = int(input())
#print "\nEnter Host 3 (H2's Neighbour)"
#h3 = int(input())

h1 = "10.0.0." + str(h1)
h2 = "10.0.0." + str(h2)
#h3 = "10.0.0." + str(h3)

flag = True

while flag:

	#Creating Graph
	G = nx.Graph()

	# Stores Info About H3 And H4's Switch
	switch = {}

	# MAC of Hosts i.e. IP:MAC
	deviceMAC = {}

	# IP of Hosts i.e. MAC:IP
	deviceIP = {}

	# Stores Switch Links To H3 and H4's Switch
	switchLinks = {}

	# Stores Host Switch Ports
	hostPorts = {}

	# Stores Switch To Switch Path
	path = {}

	# Stores Link Ports
	linkPorts = {}

	# Stores Final Link Rates
	finalLinkTX = {}

	# Store Port Key For Finding Link Rates
	portKey = ""

	# Statistics
	global stats
	stats = ""

	# Stores Link Cost
	global cost
	cost = 0

	try:
 		# Get the Device Info using response in ODL controller (Switch To Which The Device Is Connected & The MAC Address Of Each Device)
		topology = "http://10.0.2.15:8181/restconf/operational/network-topology:network-topology"
		getResponse(topology,"topology")

		# Print Device:MAC Info
		print "\nDevice IP & MAC\n"
		print deviceMAC

		# Print Switch:Device Mapping
		print "\nSwitch:Device Mapping\n"
		print switch

		# Print Host:Port Mapping
		print "\nHost:Port Mapping To Switch\n"
		print hostPorts

		# Print Switch:Switch Port:Port Mapping
		print "\nSwitch:Switch Port:Port Mapping\n"
		print linkPorts

		# Paths
		print "\nAll Paths\n"
		#for path in nx.all_simple_paths(G, source=2, target=1):
			#print(path)
		for path in nx.all_shortest_paths(G, source=int(switch[h2].split(":",1)[1]), target=int(switch[h1].split(":",1)[1]), weight=None):
			print path

		# Cost Computation
		# Find the shortest path using cost calculation
		tmp = ""
		for currentPath in nx.all_shortest_paths(G, source=int(switch[h2].split(":",1)[1]), target=int(switch[h1].split(":",1)[1]), weight=None):
			for node in range(0,len(currentPath)-1):
				tmp = tmp + str(currentPath[node]) + "::"
				key = str(currentPath[node])+ "::" + str(currentPath[node+1])
				port = linkPorts[key]
				port = port.split(":",1)[0]
				port = int(port)
				stats = "http://10.0.2.15:8181/restconf/operational/opendaylight-inventory:nodes/node/openflow:"+str(currentPath[node])+"/node-connector/openflow:"+str(currentPath[node])+":"+str(port)
				getResponse(stats,"statistics")
			tmp = tmp + str(currentPath[len(currentPath)-1])
			tmp = tmp.strip("::")
			finalLinkTX[tmp] = cost
			cost = 0
			tmp = ""

		print "\nFinal Link Cost\n"
		print finalLinkTX
		# find shortest path 
		shortestPath = min(finalLinkTX, key=finalLinkTX.get)
		print "\n\nShortest Path: ",shortestPath
		
		# push the shortest path to the "pushFlowRules" function
		pushFlowRules(shortestPath)

		time.sleep(60)
	except KeyboardInterrupt:
		break
		exit