import RPi.GPIO as GPIO

class Luz_rgb:
	def __init__(self, r, g, b):
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(r, GPIO.OUT)
		GPIO.output(r, True)
		self.r = GPIO.PWM(r, 100) # 100 Hz
		self.r.start(0)

		GPIO.setup(g, GPIO.OUT)
		GPIO.output(g, True)
		self.g = GPIO.PWM(g, 100) # 100 Hz
		self.g.start(0)

		GPIO.setup(b, GPIO.OUT)
		GPIO.output(b, True)
		self.b = GPIO.PWM(b, 100) # 100 Hz
		self.b.start(0)

	def pinOn(self, pwm_object, freq=100):
		pwm_object.ChangeDutyCycle(freq)

	def pinOff(self, pwm_object):
		pwm_object.ChangeDutyCycle(0)

	def red(self, freq=100):
		self.pinOn(self.r, freq)
		self.pinOff(self.g)
		self.pinOff(self.b)

	def white(self, freq=100):
		self.pinOn(self.r, freq)
		self.pinOn(self.g, freq)
		self.pinOn(self.b, freq)

	def yellow(self, freq=100):
		self.pinOn(self.r, freq)
		self.pinOn(self.g, freq)
		self.pinOff(self.b)

	def green(self, freq=100):
		self.pinOff(self.r)
		self.pinOn(self.g, freq)
		self.pinOff(self.b)

	def blue(self, freq=100):
		self.pinOff(self.r)
		self.pinOff(self.g)
		self.pinOn(self.b, freq)

	def turnOff(self):
		self.pinOff(self.r)
		self.pinOff(self.g)
		self.pinOff(self.b)