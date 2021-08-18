import math
class Vec3:
	def __init__(self,x,y,z):
		self.x = x
		self.y = y
		self.z = z
		
def NormalizeSpeed(speed, max_speed,count = 0):
	if count > 10:
		print("Normalize Speed cannot converge!", speed, max_speed)
		exit()
	x = speed[0]
	y = speed[1]
	z = speed[2]

	scalar = math.sqrt(pow(x,2) + pow(y,2) + pow(z,2))
	if scalar > max_speed:
		return NormalizeSpeed([x/scalar*max_speed, y/scalar*max_speed, z/scalar*max_speed],max_speed,count+1) # will be changed
	return speed


