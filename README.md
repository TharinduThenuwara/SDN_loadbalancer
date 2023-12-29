# SDN Load Balancer

## Overview

This project implements a simple Load Balancer using Software-Defined Networking (SDN) principles. The network is created using Mininet, and the OpenDayLight SDN controller is employed to handle traffic and distribute it among multiple hosts.

## Features

- Load balancing of network traffic using SDN.
- Mininet is used to simulate the network topology.
- OpenDayLight SDN controller manages the SDN environment.

## Prerequisites

Make sure you have the following software installed before running the project:

- Mininet
- OpenDayLight SDN Controller

## Customizing the Network Topology

![WhatsApp Image 2023-12-29 at 6 52 29 PM](https://github.com/TharinduThenuwara/SDN_loadbalancer/assets/72153792/a572b8c7-a0d5-46c0-8b08-a1078ea6fcd6)

The network topology used in this project can be customized to meet specific requirements. The network topology is defined in the `Topology.py` file. You can modify this file to create a customized network layout. For example, you can adjust the number of hosts, switches, and links, as well as their connections.

![image](https://github.com/TharinduThenuwara/SDN_loadbalancer/assets/72153792/77cd7957-bfe3-4391-a511-29c268f015e4)

To customize the network topology:

1. Open the `Topology.py` file in a text editor.
2. Modify the topology by adding, removing, or adjusting hosts, switches, and links.
3. Save the file.

