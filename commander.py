
import datetime
import time
import logging
from typing import Dict
import collections
import threading

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from swarm import Swarm
from cflib.crazyflie.syncLogger import SyncLogger


from Uav import *
from missions import *
from Groups import *
from Utils import *

import math
import traceback
import subprocess, sys

# Change uris and sequences according to your setup
logging.basicConfig(level=logging.ERROR)

deques = [collections.deque(maxlen=1)] * 5
logs = [""]*Max_Uav_Number

def Pos_thread(sequence):
	append = sequence[0]
	process = sequence[1]
	print(append)
	while 1:
		x = datetime.datetime.now()
		for line in iter(process.stdout.readline, ""):



			lst = line.split("/")[1:]
			uavList[int(lst[0]) - 1].info["X"] = -float(lst[1])
			uavList[int(lst[0]) - 1].info["Y"] = float(lst[2])
			uavList[int(lst[0]) - 1].info["Z"] = -float(lst[3])
			#print("pose thread time is",datetime.datetime.now() - x, line)
			#print(line)

		#print("problem!")
	#print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
	# DO NOT DELETE THIS

class Commander:


	def init_swarm(self,uris):
		self.seq_args = {}
		
		self.pose_args = {}
		cflib.crtp.init_drivers(enable_debug_driver=False)
		for uri in range(len(uris)):
			self.seq_args[uris[uri]] = [[uri]]
			p = subprocess.Popen("stdbuf -o0 python poses.py" + " {}".format(uri+1), shell=True, stdout=subprocess.PIPE, universal_newlines=True) 
			self.pose_args[uris[uri]] = [[deques[uri],p]]
			t = threading.Thread(target = Pos_thread,args = ([uri,p],))
			t.start()

		factory = CachedCfFactory(rw_cache='./cache')


		with Swarm(uris, factory=factory) as swarm:

			swarm.parallel(wait_for_param_download)

			#swarm.parallel(Pos_thread,args_dict = self.pose_args)

			swarm.parallel(run_sequence , args_dict = self.seq_args )


	
def land(cf,DroneID ,height = 0.1,time1 = 0.5):
	landTime = time.time() + time1
	uavList[DroneID].SetDest(uavList[DroneID].info["X"],uavList[DroneID].info["Y"] , height)
	while uavList[DroneID].info["Z"] > 0.25 :
		speed = uavList[DroneID].calculate_speed()
		cf.commander.send_velocity_world_setpoint(speed[0], speed[1], speed[2], 0)

	uavList[DroneID].info["X"] = 0.0
	uavList[DroneID].info["Y"] = 0.0
	uavList[DroneID].info["Z"] = 0.0
def wait_for_param_download(scf):
	while not scf.cf.param.is_updated:
		time.sleep(1.0)
	ConsoleOutput('Parameters downloaded for '+str(scf.cf.link_uri))


charging_problem = 0
def ReadBattery(charge):
	global charging_problem
	charge_percent = (charge - 3.0) / (4.23 - 3.0) # https://forum.bitcraze.io/viewtopic.php?t=732
	if charge_percent < 15:
		charging_problem+=1
		if charging_problem > 1e6:
			print("Crazyflie {} has {}%% battery left, landing.".format(DroneID,charge_percent))
			uav_list[DroneID].info["Bağlı"] = "Hayır"
			land(cf,DroneID)
			return False
	return True
			

def run_sequence(scf,sequence):
	
	try:	
		cf = scf.cf
		DroneID = sequence[0]
		
		while cf.is_connected() == False:
			time.sleep(0.01)
		uavList[DroneID].info["Bağlı"] = "Evet"
		uavList[DroneID].SetState(State.CONNECTED)
		
		### LOG INFOS (Konum ve Batarya çek)
		lg_stab = LogConfig(name='log', period_in_ms=10)
		lg_stab.add_variable('stateEstimate.x', 'float')
		lg_stab.add_variable('stateEstimate.y', 'float')
		lg_stab.add_variable('stateEstimate.z', 'float')
		lg_stab.add_variable('pm.vbat' , 'float')

		logger = SyncLogger(scf, lg_stab)
		logger.connect()
		info = logger._queue.get()[1]
		### LOG INFOS




		#uavList[DroneID].SetDest(uavList[DroneID].info["X"] , uavList[DroneID].info["Y"],1.0)
		while uavList[DroneID].GetState() != State.NOT_CONNECTED:
			
			
			info = logger._queue.get()[1]
			#uavList[DroneID].Update(info["stateEstimate.x"],info["stateEstimate.y"],info["stateEstimate.z"],info["pm.vbat"])
			uavList[DroneID].info["Batarya"] = info["pm.vbat"]
			"""if ReadBattery(info["pm.vbat"]) == False:
				uavList[DroneID].SetState(State.LOW_BATTERY)
				ConsoleOutput("UAV {} has low percent battery.".format(DroneID))
				return"""
			
			speed = uavList[DroneID].calculate_speed()
			

			dest = uavList[DroneID].GetDest()
			if speed is not None:
				logs[DroneID] += "{},{},{},{},{},{},{},{},{},{}\n".format(uavList[DroneID].GetState().name,uavList[DroneID].info["X"],uavList[DroneID].info["Y"],uavList[DroneID].info["Z"],speed[0],speed[1],speed[2],dest[0],dest[1],dest[2])
			else:
				logs[DroneID] += "{},{},{},{},{},{},{},{},{},{}\n".format(uavList[DroneID].GetState().name,uavList[DroneID].info["X"],uavList[DroneID].info["Y"],uavList[DroneID].info["Z"],-math.pi,-math.pi,-math.pi,dest[0],dest[1],dest[2])
			#logs[DroneID] += uavList[DroneID].GetState().name + "," + str(uavList[DroneID].info["X"]) + "," + str(uavList[DroneID].info["Y"]) + "," + str(uavList[DroneID].info["Z"]) + "," + str(speed[0]) + "," + str(speed[1]) + "," + str(speed[2]) + "\n"
			if speed is not None:
				collision_speed = uavList[DroneID].CalculateCollisionSpeed()
				cf.commander.send_velocity_world_setpoint(collision_speed[0] + speed[0], collision_speed[1] + speed[1], speed[2] + collision_speed[2], 0)
				pass
		ConsoleOutput("Connection is broken with UAV {}".format(DroneID))

	except Exception as e:
		print(e)
		print("asd")
		uavList[DroneID].SetState(State.NOT_CONNECTED)
		groups.RemoveUav(uavList[DroneID].info["Grup"] , DroneID)
		traceback.print_exc()		
	



commander = Commander()
