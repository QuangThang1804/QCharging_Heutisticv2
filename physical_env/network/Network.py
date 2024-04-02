import copy
import numpy as np
import optimizer
from optimizer.utils import network_clustering
from physical_env.network.utils import network_clustering
class Network:
    def __init__(self, env, listNodes, baseStation, listTargets, mc_list = None, max_time = None):
        self.env = env
        self.listNodes = listNodes
        self.baseStation = baseStation
        self.listTargets = listTargets
        self.targets_active = [1 for _ in range(len(self.listTargets))]
        self.alive = 1
        # Setting BS and Node environment and network
        baseStation.env = self.env
        baseStation.net = self
        self.max_time = max_time
        self.mc_list = mc_list
        self.network_cluster = []

        self.frame = np.array([self.baseStation.location[0], self.baseStation.location[0], self.baseStation.location[1], self.baseStation.location[1]], np.float64)
        it = 0
        for node in self.listNodes:
            node.id = it
            node.env = self.env
            node.net = self
            it += 1
            self.frame[0] = min(self.frame[0], node.location[0])
            self.frame[1] = max(self.frame[1], node.location[0])
            self.frame[2] = min(self.frame[2], node.location[1])
            self.frame[3] = max(self.frame[3], node.location[1])
        self.nodes_density = len(self.listNodes) / ((self.frame[1] - self.frame[0]) * (self.frame[3] - self.frame[2]))
        it = 0

        # Setting name for each target
        for target in listTargets:
            target.id = it
            it += 1
         

    # Function is for setting nodes' level and setting all targets as covered
    def setLevels(self):
        for node in self.listNodes:
            node.level = -1
        tmp1 = []
        tmp2 = []
        for node in self.baseStation.direct_nodes:
            if node.status == 1:
                node.level = 1
                tmp1.append(node)

        for i in range(len(self.targets_active)):
            self.targets_active[i] = 0

        while True:
            if len(tmp1) == 0:
                break
            # For each node, we set value of target covered by this node as 1
            # For each node, if we have not yet reached its neighbor, then level of neighbors equal this node + 1
            for node in tmp1:
                for target in node.listTargets:
                    self.targets_active[target.id] = 1
                for neighbor in node.neighbors:
                    if neighbor.status == 1 and neighbor.level == -1:
                        tmp2.append(neighbor)
                        neighbor.level = node.level + 1

            # Once all nodes at current level have been expanded, move to the new list of next level
            tmp1 = tmp2[:]
            tmp2.clear()
        return


    def operate(self, t=1, optimizer=None):
        request_id = []
        for node in self.listNodes:
            self.env.process(node.operate(t=t))
        self.env.process(self.baseStation.operate(t=t))

        while True:
            yield self.env.timeout(t / 10.0)
            self.setLevels()
            self.alive = self.check_targets()
            yield self.env.timeout(10)
            if not self.network_cluster:
                self.network_cluster = network_clustering(network=self)
                optimizer.action_list = self.network_cluster
            yield self.env.timeout(9.0 * t / 10.0)
            # optimizer.action_list = network_clustering(optimizer=optimizer, network=self, nb_cluster=83)
            for index, node in enumerate(self.listNodes):
                if node.energy <= node.threshold:
                    node.request(optimizer = optimizer, t=t)
                    # print(optimizer.list_request)
                    request_id.append(index)
                else:
                    node.is_request = False

            # if (request_id):
            #     print(len(request_id))
            #     print(request_id)
            # for request in optimizer.list_request:
            #     print(request)
            if optimizer and self.alive:
                for mc in self.mc_list:
                    self.env.process(mc.operate_step_v3(net=self, optimizer=optimizer, time_stem=t))
            # if self.alive == 0 or self.env.now >= self.max_time:
            if self.alive == 0:
                break
        return

    # If any target dies, value is set to 0
    def check_targets(self):
        return min(self.targets_active)
    
    def check_nodes(self):
        tmp = 0
        for node in self.listNodes:
            if node.status == 0:
                tmp += 1
        return tmp

    def avg_network(self):
        sum = 0
        for node in self.listNodes:
            sum += node.energy
        return sum / len(self.listNodes)

    def min_node(self):
        id_node_min = -1
        min_energy = 1000000000
        for id, node in enumerate(self.listNodes):
            if node.energy < min_energy:
                min_energy = node.energy
                id_node_min = id
        return id_node_min