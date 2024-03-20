import RPi.GPIO as GPIO
import time
import sys
import signal
import threading
import json
from luz_rgb import Luz_rgb

# Configuramos el modo de numeración de los pines GPIO (BCM)
GPIO.setmode(GPIO.BCM)

# Definimos los números de los pines GPIO que vamos a utilizar
BUTTON_GPIO = 23
TRIGGER_ULTRA_GPIO = 24
ECHO_ULTRA_GPIO = 25
LDR_GPIO = 4
MOTOR_VELOCIDAD_GPIO = 13
MOTOR_DIRECCION1_GPIO = 5
MOTOR_DIRECCION2_GPIO = 6
SERVO_GPIO = 16

# Configuramos el pin del botón como entrada y activamos la resistencia pull-up. Esto significa que el pin estará en HIGH cuando no se presione el botón
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# El pin Trigger se establece como salida para activar el sensor ultrasónico
GPIO.setup(TRIGGER_ULTRA_GPIO, GPIO.OUT)
# El pin Echo se establece como entrada para recibir el eco del pulso ultrasónico
GPIO.setup(ECHO_ULTRA_GPIO, GPIO.IN)
# Los pines del motor se establecen como salida
GPIO.setup(MOTOR_VELOCIDAD_GPIO, GPIO.OUT)
GPIO.setup(MOTOR_DIRECCION1_GPIO, GPIO.OUT)
GPIO.setup(MOTOR_DIRECCION2_GPIO, GPIO.OUT)
# El pin del servomotor se establece como salida
GPIO.setup(SERVO_GPIO, GPIO.OUT)

# Creamos un objeto PWM para controlar la velocidad del motor y lo inicializamos
dc_motor_object = GPIO.PWM(MOTOR_VELOCIDAD_GPIO, 100)  # 100 Hz
GPIO.output(MOTOR_DIRECCION1_GPIO, True)  # Girará en la dirección 1
GPIO.output(MOTOR_DIRECCION2_GPIO, False)  # No girará en la dirección 2
GPIO.output(MOTOR_VELOCIDAD_GPIO, True)  # Tendrá velocidad
dc_motor_object.start(100)
dc_motor_object.ChangeDutyCycle(0)  # Inicialmente la velocidad del motor es 0
# Creamos un objeto PWM para controlar el servomotor y lo inicializamos
servo_object = GPIO.PWM(SERVO_GPIO, 50)  # 50 Hz
servo_object.start(0)

# Creamos un objeto para controlar la luz RGB
luz_trasera_derecha = Luz_rgb(17, 27, 22)
luz_trasera_izquierda = Luz_rgb(14, 15, 20)

# Variable global para controlar si el programa debe seguir ejecutando los comandos o no
should_run = False

# Variable global para almacenar el tiempo que falta para que se ejecute el siguiente comando
time_to_next_command = 0

# Variable global para almacenar el comando actual que se está ejecutando
comando_actual = True

# Variable global para almacenar la luminosidad
luminosidad_actual = 0

distancia_actual = 0

# Variable global para almacenar el angulo del servomotor/vehiculo
angulo_actual = 0

# Variable global para almacenar la velocidad actual del vehiculo
velocidad_actual = 0

# Variable global para almacenar la velocidad previa del vehiculo
velocidad_previa = 0

# Variable global para controlar si el vehiculo debe frenar
frenando = False

def signal_handler(sig, frame):
    # Limpiamos los pines GPIO antes de salir (los pines utilizados se estabelecen como entrada)
    GPIO.cleanup()
    print("\nPines GPIO limpiados. Programa terminado.")
    dc_motor_object.ChangeDutyCycle(0)  # Paramos el motor
    setAngle(90)  # Establecemos el servomotor en 90 grados
    time.sleep(2) # Esperamos 1 segundo para que de tiempo a detenerse
    sys.exit(0)  # Sale del programa

def button_callback(channel):
    global should_run
    should_run = not should_run
    print("Botón presionado", should_run)


# Función que mide la distancia. Devuelve la distancia en centímetros
def obtener_distancia(pin_trigger, pin_echo):
    global should_run
    global distancia_actual
    while should_run:
        # Enviamos un pulso ultrasónico por el pin Trigger para activar el sensor
        GPIO.output(pin_trigger, GPIO.HIGH)
        time.sleep(
            0.00001)  # Esperamos 0.01 milisegundos para asegurarnos de que el pulso ultrasónico se envía correctamente
        GPIO.output(pin_trigger, GPIO.LOW)  # Desactivamos el pulso ultrasónico

        # Esperamos a que el pin Echo esté encendido para iniciar la medición del tiempo
        while not GPIO.input(pin_echo) == True:
            tiempo_inicial = time.time()

        # Esperamos a que el pin Echo se apague (ya no se recibe el eco del pulso ultrasónico)
        while GPIO.input(pin_echo) == True:
            tiempo_final = time.time()

        # Calculamos la duración del pulso ultrasónico
        tiempo_total = tiempo_final - tiempo_inicial

        # Calculamos la distancia multiplicando por la velocidad del sonido (34300 cm/s) y dividiendola por 2 debido a la ida y vuelta de la señal
        distancia_actual = (tiempo_total * 34300) / 2

        print("Distancia", distancia_actual)
        time.sleep(10)
    return

# Función que mide la luminosidad. Devuelve el tiempo que tarda en cargarse el condensador
def obtener_luminosidad(pin_ldr):
    global should_run
    global luminosidad_actual
    while should_run:
        # Contador para medir el tiempo que tarda en cargarse el condensador. Inicialmente a 0
        count = 0

        # El pin del sensor de luminosidad se establece como salida
        GPIO.setup(LDR_GPIO, GPIO.OUT)
        # Ponemos el pin en bajo para descargar el condensador
        GPIO.output(pin_ldr, GPIO.LOW)
        # Esperamos 100 milisegundos para asegurarnos de que se ha descargado el condensador por completo
        time.sleep(0.1)

        # Cambiamos el pin a entrada
        GPIO.setup(pin_ldr, GPIO.IN)
        # Mientras el pin esté en bajo, incrementamos el contador. Cuando el condensador se cargue a 3/4, el pin pasará a alto
        while (GPIO.input(pin_ldr) == GPIO.LOW):
            count += 1

        # Actualizamos el valor de la luminosidad
        luminosidad_actual = count

        # Devolvemos un valor que representa cuantas unidades de tiempo tarda en cargarse el condensador. Esto nos sirve para medir la luminosidad
        print("Luminosidad:", luminosidad_actual)
        time.sleep(2)
    return

def controlar_vehiculo():
    global should_run
    global comando_actual
    global time_to_next_command
    # Thread para actualizar el tiempo que falta para el siguiente comando
    thread_time_to_next_command = threading.Thread(target=actualizar_tiempo_siguiente_comando, args=(),
                                                   daemon=True)
    thread_time_to_next_command.start()

    # Variable para controlar si el comando actual se está ejecutando
    command_is_running = False

    # Mientras el botón esté presionado y haya comandos por ejecutar, ejecutamos los comandos
    while should_run and comando_actual:
        # Si el comando anterior ha terminado, obtenemos el siguiente comando
        if time_to_next_command <= 0.0:
            comando_actual = obtener_siguiente_comando()
            # Si hay un comando, lo ejecutamos
            if comando_actual:
                time_to_next_command = comando_actual['Time']
                execute_command()
                command_is_running = True
            # Si no hay comandos, paramos el vehículo
            else:
                print("No hay más comandos")
                comando_actual = False
                return
        # Si el comando anterior no ha terminado, continuamos ejecutándolo el tiempo que queda (variable global time_to_next_command)
        else:
            # Si no se está ejecutando ningún comando, ejecutamos el comando actual. Aquí se entrará cuando se haya pulsado el botón y se tenga que segiuir ejecutando el comando que estaba en ejecución antes de pulsar el botón.
            if not command_is_running:
                execute_command()
    return

def controlar_luces():
    global should_run
    global luminosidad_actual
    global angulo_actual
    global luz_trasera_derecha
    global luz_trasera_izquierda
    global frenando
    while should_run and comando_actual:
        # Intermitencia
        if (angulo_actual > 100):
            luz_trasera_derecha.turnOff()
            luz_trasera_izquierda.turnOff()

            # Intermitencia 1 (1/6 de segundo encendidas, 1/6 de segundo apagadas)
            luz_trasera_izquierda.yellow()
            time.sleep(0.166)
            luz_trasera_izquierda.turnOff()
            time.sleep(0.166)
            # Intermitencia 2 (1/6 de segundo encendidas, 1/6 de segundo apagadas)
            luz_trasera_izquierda.yellow()
            time.sleep(0.166)
            luz_trasera_izquierda.turnOff()
            time.sleep(0.166)
            # Intermitencia 3 (1/6 de segundo encendidas, 1/6 de segundo apagadas)
            luz_trasera_izquierda.yellow()
            time.sleep(0.166)
            luz_trasera_izquierda.turnOff()
            time.sleep(0.166)

        elif (angulo_actual < 80):
            luz_trasera_derecha.turnOff()
            luz_trasera_izquierda.turnOff()

            # Intermitencia 1 (1/6 de segundo encendidas, 1/6 de segundo apagadas)
            luz_trasera_derecha.yellow()
            time.sleep(0.166)
            luz_trasera_derecha.turnOff()
            time.sleep(0.166)
            # Intermitencia 2 (1/6 de segundo encendidas, 1/6 de segundo apagadas)
            luz_trasera_derecha.yellow()
            time.sleep(0.166)
            luz_trasera_derecha.turnOff()
            time.sleep(0.166)
            # Intermitencia 3 (1/6 de segundo encendidas, 1/6 de segundo apagadas)
            luz_trasera_derecha.yellow()
            time.sleep(0.166)
            luz_trasera_derecha.turnOff()
            time.sleep(0.166)

        # Luces de freno
        elif frenando:
            luz_trasera_derecha.red(100)
            luz_trasera_izquierda.red(100)

        # Luces de posición
        elif luminosidad_actual > 30000:
            luz_trasera_derecha.red(50)
            luz_trasera_izquierda.red(50)

        # Luces apagadas cuando hay suficiente luminosidad
        elif luminosidad_actual < 30000:
            luz_trasera_derecha.turnOff()
            luz_trasera_izquierda.turnOff()
    return

def execute_command():
    global dc_motor_object
    global should_run
    global angulo_actual
    global velocidad_actual
    global velocidad_previa
    global frenando
    if should_run:
        print("Ejecutando", comando_actual, "durante", time_to_next_command, "segundos")
        velocidad_previa = velocidad_actual
        velocidad_actual = comando_actual['Speed']
        # Si la velocidad actual es menor que la velocidad previa, el vehículo está frenando
        if velocidad_actual < velocidad_previa:
            frenando = True
            print("Frenando...")

        else:
            frenando = False
        angulo_actual = comando_actual['SteeringAngle']
        dc_motor_object.ChangeDutyCycle(velocidad_actual)
        setAngle(angulo_actual)
        # Esperamos el tiempo que hay hasta el siguiente comando
        time.sleep(time_to_next_command)

def setAngle(angle):
    global servo_object
    # Limitamos el ángulo entre 0 y 180 grados
    angle = max(0, min(180, angle))
    start = 4  # 0 grados --> 4% de ciclo de trabajo
    end = 12.5  # 180 grados --> 12.5% de ciclo de trabajo
    ratio = (end - start) / 180
    angle_as_percentage = angle * ratio + start
    # Movemos el servomotor al ángulo deseado
    servo_object.ChangeDutyCycle(angle_as_percentage)


def load_commands():
    global vehicle_control_commands
    file = open('./commands.json')
    vehicle_control_commands = json.load(file)
    file.close()


def obtener_siguiente_comando():
    global vehicle_control_commands
    # Si hay comandos en la lista, devolvemos el siguiente comando
    if vehicle_control_commands:
        return vehicle_control_commands.pop(0)
    else:
        return None


def actualizar_tiempo_siguiente_comando():
    global time_to_next_command
    global should_run
    # Mientras should_run sea True, actualizamos el tiempo que falta para el siguiente comando
    while should_run and comando_actual:
        print("Tiempo restante para el siguiente comando:", time_to_next_command, "segundos")
        if time_to_next_command > 0:
            time_to_next_command -= 0.5
            time.sleep(0.5)
    return


if __name__ == "__main__":
    # Asociamos la función de callback a la interrupción --> RISING (cuando el botón se presiona)
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.RISING, callback=button_callback,
                          bouncetime=100)  # El botón se ha presionado
    # Asociamos la función de callback a la interrupción de teclado (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    load_commands()  # Cargamos los comandos del archivo commands.json

    while True:
        if should_run:
            # Medimos la distancia
            thread_sensor_ultrasonidos = threading.Thread(target=obtener_distancia,
                                                          args=(TRIGGER_ULTRA_GPIO, ECHO_ULTRA_GPIO), daemon=True)
            # Medimos la luminosidad
            thread_ldr = threading.Thread(target=obtener_luminosidad, args=(LDR_GPIO,), daemon=True)
            # Activamos el motor
            thread_vehiculo = threading.Thread(target=controlar_vehiculo, args=(), daemon=True)
            # Controlamos las luces
            thread_controlar_luces = threading.Thread(target=controlar_luces, args=(), daemon=True)

            thread_vehiculo.start()
            thread_sensor_ultrasonidos.start()
            thread_ldr.start()
            thread_controlar_luces.start()

            thread_vehiculo.join()
            # Si el botón se ha pulsado o se han agotado los comandos, paramos el vehículo
            print("Vehiculo parado")

            # Cuando el hilo del vehículo termina, ya sea por que no existen mas comandos o porque se ha pulsado el botón, paramos el motor y el servomotor
            dc_motor_object.ChangeDutyCycle(0)  # Paramos el motor
            setAngle(90)  # Establecemos el servomotor en 90 grados

            thread_controlar_luces.join()
            # Apagamos las luces
            luz_trasera_izquierda.turnOff()
            luz_trasera_derecha.turnOff()

            thread_sensor_ultrasonidos.join()
            thread_ldr.join()
            # Si el botón se ha pulsado, se apaga el vehiculo (se dejan de medir distancias y luminosidad)
            print("Vehículo apagado")
