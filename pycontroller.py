import signal
import socket
import pygame
import time

pygame.init()
def main():
    clock = pygame.time.Clock()
    print("Starting py controller")
    broadcast_port = 60000
    found_ip = 0
    joysticks = {}
    while(found_ip == 0):
        ret_data = receive_broadcast_packet(broadcast_port, 1024)
        ret_string = str(ret_data[0].decode())
        fixed_string = "picow:"
        if(fixed_string in ret_string):
            print("Found:",ret_string)
            rand = int(ret_string[len(fixed_string):])
            addr = ret_data[1][0]
            port = ret_data[1][1]
            print(rand,addr,port)
            if(rand and addr and port):
                found_ip = 1
                test_packet = "pycontroller:"+str(rand)
                send_udp_packet(addr, broadcast_port+rand,test_packet)
        else:
            print(ret_string)
    while(1):
        # Event processing step.
        # Possible joystick events: JOYAXISMOTION, JOYBALLMOTION, JOYBUTTONDOWN,
        # JOYBUTTONUP, JOYHATMOTION, JOYDEVICEADDED, JOYDEVICEREMOVED
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True  # Flag that we are done so we exit this loop.

            if event.type == pygame.JOYBUTTONDOWN:
                #print("Joystick button pressed.")
                #if event.button == 0:
                    #joystick = joysticks[event.instance_id]
                    #if joystick.rumble(0, 0.7, 500):
                        #print(f"Rumble effect played on joystick {event.instance_id}")
                pass

            if event.type == pygame.JOYBUTTONUP:
                #print("Joystick button released.")
                pass

            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connencted")

            if event.type == pygame.JOYDEVICEREMOVED:
                del joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")
        
        joystick_count = pygame.joystick.get_count()
        if(joystick_count == 0):
            test_packet = "pycontroller:"+str(rand)
            #print("No controller, sending dummy packet")
            send_udp_packet(addr, broadcast_port+rand,test_packet)
            time.sleep(0.5)
        else:
            for controller in joysticks.values():
                joystick = controller
                break
            joystick_data = []
            axes = joystick.get_numaxes()
            for i in range(axes):
                axis = joystick.get_axis(i)
                joystick_data.append(axis)
            buttons = joystick.get_numbuttons()
            for i in range(buttons):
                button = joystick.get_button(i)
                joystick_data.append(button)
            hats = joystick.get_numhats()
            for i in range(hats):
                hat = joystick.get_hat(i)
                joystick_data.append(hat)
            
            test_packet = "pycontroller:"+str(rand)
            for data in joystick_data:
                test_packet = test_packet + ":" + str(data)
            print(joystick_data)
            send_udp_packet(addr, broadcast_port+rand,test_packet)
        clock.tick(30)

def send_broadcast_packet(packet_port, packet_data):
   udp_tx_sock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
   udp_tx_sock.bind(('',0))
   udp_tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
   udp_tx_sock.sendto(packet_data, ('<broadcast>', packet_port))
   udp_tx_sock.close()

def receive_broadcast_packet(packet_port, packet_length):
   global udp_rx_sock
   udp_rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   udp_rx_sock.bind(('',packet_port))
   udp_packet_data = udp_rx_sock.recvfrom(packet_length)
   udp_rx_sock.close()
   return udp_packet_data

def send_udp_packet(packet_ip, packet_port, packet_data):
   udp_tx_sock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
   udp_tx_sock.bind(('',0))
   udp_tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
   udp_tx_sock.sendto(packet_data.encode(), (packet_ip, packet_port))
   udp_tx_sock.close()

def config_interrupts():
   print("Setting Up Interrupt Handler")
   try:
      signal.signal(signal.SIGINT, exit_handler)
   except:
      print("Couldn't lock SIGINT")
   try:
      signal.signal(signal.SIGBREAK, exit_handler)
   except:
      print("Couldn't lock SIGBREAK")
   try:
      signal.signal(signal.SIGKILL, exit_handler)
   except:
      print("Couldn't lock SIGKILL")
   try:
      signal.signal(signal.SIGQUIT, exit_handler)
   except:
      print("Couldn't lock SIGQUIT")


def exit_handler(signum, frame):
   print("caught exit... shutting down")
   # other cleanup code here
   
   #main_thread.stop_thread()

if __name__ == "__main__":
   main()
   # try:
   #    config_interrupts()
   #    main_thread.start(main)
   #    while(main_thread.is_active()):
   #       main_thread.pause(1)
   # except KeyboardInterrupt:
   #    pass