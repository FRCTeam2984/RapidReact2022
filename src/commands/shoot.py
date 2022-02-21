import math, ctre, wpilib
from rev import RelativeEncoder
from subsystems.drive import Drive
from subsystems.shooter import Shooter
from utils import math_functions, ID

class Shoot:
   TURNING = 0
   MOVING = 1
   SHOOTING = 2
   DISCARDING = 3
   IDLE = 4
   POSITIONING = 5
   SPINNING = 6
   FIRING = 7
   RELAXING = 8
   DEFAULT = -1
   state = TURNING
   min_LimelightDistance = 15 #angle
   max_LimelightDistance = 0 #angle
   flywheel_desiredSpeed = 0

   def __init__(self, _drive : Drive, _shooter : Shooter):
      self.drive = _drive
      self.shooter = _shooter
      self.target_angle = self.drive.getYaw() - 180

   def turning(self, motor_power_multiplyer):
      if self.shooter.hasTarget():
         delta_angle = self.shooter.getCameraInfo()[1] # get angle of target
         self.target_angle = self.drive.getYaw() - delta_angle
         if abs(delta_angle) < 2: # if aim is accurate enough
            self.state = self.MOVING # set state to shooting
      self.drive.absoluteDrive(0, 0, self.target_angle, motor_power_multiplyer)

   def moving(self):
      if self.ball_color == self.alliance_color:
         self.state = self.SHOOTING
      else:
         self.state = self.DISCARDING

   def positioning(self, motor_power_multiplyer):
      power = 0
      delta_angle = self.shooter.getCameraInfo()[1] # get angle of target
      self.target_angle = self.drive.getYaw() - delta_angle
      if self.shooter.getCameraInfo()[2] > self.min_LimelightDistance:
         power = .5
      if self.shooter.getCameraInfo()[2] < self.max_LimelightDistance:
         power = -.5
      if not self.shooter.hasTarget():
         power = 0
         self.target_angle = self.drive.getYaw()
      self.drive.absoluteDrive(power, 0, self.target_angle, motor_power_multiplyer)
      print ("limelight x, limelight y: ", self.shooter.getCameraInfo()[1], self.shooter.getCameraInfo()[2])
      return (power == 0 and abs(delta_angle) < 2 and self.shooter.hasTarget())

   def spinning(self, ball, motor_power_multiplyer):
      delta_angle = self.shooter.getCameraInfo()[1] # get angle of target
      self.target_angle = self.drive.getYaw() - delta_angle
      if ball == False:
         self.target_angle -= 30 # shoot away from target
      self.drive.absoluteDrive(0, 0, self.target_angle, motor_power_multiplyer)
      self.flywheel_desiredSpeed = math_functions.shootInterp(self.shooter.getCameraInfo()[2])
      return (abs(delta_angle) < 2)

   def firing(self):
      self.flywheel_desiredSpeed = math_functions.shootInterp(self.shooter.getCameraInfo()[2])
      self.shooter.transportServo.setAngle(180)

   def spin_pid(self, debug):
      current_vel = self.shooter.shooterMotor.getSelectedSensorVelocity(0)
      delta = self.flywheel_desiredSpeed - current_vel
      pwr = delta * 0.001
      if (pwr > 0.99):
         pwr = 0.99
      if (pwr < -0.5):
         pwr = -0.5
      if (self.flywheel_desiredSpeed == 0):
         pwr = 0
      self.shooter.shooterMotor.set(ctre.TalonFXControlMode.PercentOutput, pwr)
      if debug:
         print ("spin: ", current_vel, " ", self.flywheel_desiredSpeed, " ", delta)
      return (abs(delta) < 600)

   def shooting(self):
      #shoot ball
      pass
   def discarding(self):
      #get rid of wrong-color ball
      pass
   
   def transporting(self, angle):
      self.shooter.transportServo.setAngle(angle)

   #always run this function in robot.py teleop
   def auto_execute(self, button_pressed, motor_power_multiplyer):
      self.spin_pid(False)
      self.flywheel_desiredSpeed = 0
      if self.state == self.IDLE:
         self.shooter.transportServo.setAngle(ID.SERVO_MIN)
         if button_pressed:
            self.ball = self.shooter.getBallStatus()
            self.shooter.printBallStatus()
            if (self.ball == True or self.ball == False) and self.shooter.hasTarget(): #if robot has ball and sees target
               self.state = self.POSITIONING
               print ("state=positioning ", self.ball)
      elif self.state == self.POSITIONING:
         # roughly turn and move into min/max distance
         if button_pressed:
            if self.positioning(motor_power_multiplyer):
               self.state = self.SPINNING
               print ("state=spinning")
         else:
            self.state = self.IDLE
            print ("state=idle")
      elif self.state == self.SPINNING:
         if button_pressed:
            if self.spinning(self.ball, motor_power_multiplyer) and self.spin_pid(True):
               self.state = self.FIRING
               print ("state=firing")
               self.startServoTime = wpilib.Timer.getFPGATimestamp()
         else:
            self.state = self.IDLE
            print ("state=idle")
      elif self.state == self.FIRING:
         if button_pressed:
            self.spinning(self.ball, motor_power_multiplyer)
            self.shooter.transportServo.setAngle(ID.SERVO_MAX)
            if self.startServoTime + 0.4 < wpilib.Timer.getFPGATimestamp():
               self.state = self.RELAXING
               print ("state=relaxing")
         else:
            self.state = self.RELAXING
      elif self.state == self.RELAXING:
         self.shooter.transportServo.setAngle(ID.SERVO_MIN)
         if self.startServoTime + 0.8 < wpilib.Timer.getFPGATimestamp():
            self.state = self.IDLE
            print ("state=idle")
      else:
         self.state = self.IDLE
         print ("state=idle")

   def finish(self):
      self.state = self.TURNING

   def execute(self, state):
      if self.state == self.TURNING:
         self.turning()
      if self.state == self.MOVING:
         self.moving()
      if self.state == self.SHOOTING: # if or elif
         #Code for shoot the ball
         self.shooting()
         #if shooting is done:
         self.finish()
      if self.state == self.DISCARDING:
         self.discarding()