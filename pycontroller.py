import signal
import socket
import pygame
import time
import serial
from array import array

pygame.init()
width = 324
height = 324
bpc = 8
cpp = 1
size = [width, height]
screen = pygame.display.set_mode(size)
black_pix = 0, 0, 0
screen.fill(black_pix)
pygame.display.flip()
image_array = array('B',(0 for _ in range(width*height)))
image_packet_size = width*height*bpc*cpp

uart_image_test = 0

def main():
    if(uart_image_test == 1):
        uart = serial.Serial ("COM8", 115200, timeout=15)
        while(1):
            get_uart_frame(uart, width, height, 1, 8)
    clock = pygame.time.Clock()
    print("Starting py controller")
    joysticks = {}
    while(1):
        broadcast_port = 60000
        found_ip = 0
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
        connected = 1
        max_timeout = 4
        while(connected):
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
            ret_image = receive_image_packet(addr, broadcast_port+rand, image_packet_size)
            if(ret_image == None):
                max_timeout = max_timeout - 1
                if(max_timeout == 0):
                    connected = 0
                    print("disconnected")
            else:
                process_packet_image(ret_image, width, height, cpp, bpc)
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

def receive_udp_packet(packet_ip, packet_port, packet_length):
    global udp_rx_sock
    udp_rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_rx_sock.settimeout(2)
    udp_rx_sock.bind(('',packet_port))
    try:
        udp_packet_data = udp_rx_sock.recvfrom(packet_length)
    except:
        udp_packet_data = None
    udp_rx_sock.close()
    return udp_packet_data

def receive_image_packet(packet_ip, packet_port, packet_length):
    global udp_rx_sock
    udp_rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_rx_sock.settimeout(2)
    udp_rx_sock.bind(('',packet_port))
    x_res = 324
    y_res = 324
    bytes_per_line_number = 4
    packet_size = x_res + bytes_per_line_number
    global image_array
    image_data = []
    found_start = 0
    found_end = 0
    last_index = 0
    try:
        while(found_start == 0):
            udp_packet_data = udp_rx_sock.recvfrom(packet_size)
            raw_data = udp_packet_data[0]
            decoded_data = list(raw_data)
            counter = 0
            index = 0
            shifter = 0
            while(counter < bytes_per_line_number):
                index = index | (decoded_data[counter] << shifter)
                shifter = shifter + 8
                counter = counter + 1
            if(index == 0):
                found_start = 1
            counter = 0
            while(counter < bytes_per_line_number):
                del decoded_data[0]
                counter = counter + 1
        x_counter = 0
        while(x_counter < x_res):
            image_array[x_res*index+x_counter] = decoded_data[x_counter]
            x_counter = x_counter + 1
        last_index = index
        while(found_end == 0):
            udp_packet_data = udp_rx_sock.recvfrom(packet_size)
            raw_data = udp_packet_data[0]
            decoded_data = list(raw_data)
            counter = 0
            index = 0
            shifter = 0
            while(counter < bytes_per_line_number):
                index = index | (decoded_data[counter] << shifter)
                shifter = shifter + 8
                counter = counter + 1
            if(index < last_index):
                print("found index rollover")
                found_end = 1
            last_index = index
            if(index == 323):
                found_end = 1
            counter = 0
            while(counter < bytes_per_line_number):
                del decoded_data[0]
                counter = counter + 1
            x_counter = 0
            while(x_counter < x_res):
                image_array[x_res*index+x_counter] = decoded_data[x_counter]
                x_counter = x_counter + 1
        print("done receiving image packet")
    except Exception as error:
        print(error)
        print("image receive error")
        udp_rx_sock.close()
        return None
    udp_rx_sock.close()
    return image_array

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

def process_packet_image(image_packet, x_res, y_res, cpp, bpc):
    try:
        image_bytes_list = image_array_to_bytes(x_res, y_res, image_packet)
        image_bytes = bytes(image_bytes_list)
        new_image = pygame.image.frombuffer(image_bytes, size, 'RGB')
        screen.blit(new_image, (0,0))
        pygame.display.flip()
    except Exception as error:
        print(error)

def get_uart_frame(uart: serial.Serial, x_res, y_res, cpp, bpc):
    pixels = x_res*y_res
    bits_per_pixel = cpp*bpc

    start_string = b'frame_start\r\n'
    end_string = b'frame_done\r\n'
    uart.flushInput()
    try:
    # search_data = uart.read_until(expected=start_string, size=len(start_string))
    # frame_data = uart.read_until(expected=end_string)
        # print("found", search_data)
        # found_frame = 0
        # found_string = 0
        # search_array = []
        # while(found_string == 0):
        #     data = uart.read()
        #     search_array.append(data)
        #     if(len(search_string) == len(search_array)):
        #         if(search_string == search_array):
        #             found_string = 1
        #         else:
        #             del search_string[0]
        #     else:
        #         pass # waiting for more data
        discard_data = None
        while(not(discard_data == start_string)):
            discard_data = uart.readline()
        frame_word = None
        frame_data = []
        while(not(frame_word == end_string)):
            if(not(frame_word == None)):
                data_string = frame_word.decode()
                data = data_string[0:-2]
                frame_data.append(data)
            frame_word = uart.readline()
        #image_data = frame_data[len(start_string)-2:-len(end_string)]
        print(len(frame_data))

    #print(image_data)
    # if(type(frame_data) == bytes):
    #     image = bytearray(frame_data)
    #     image_array = array('I', frame_data)
    #     print("Found array")
        process_image_bytes(x_res, y_res, cpp, bpc, frame_data)
    # else:
    #     print("Found other type...")
    #     print(type(frame_data))
    #print(frame_data)
    except Exception as e:
        print(e)
        #print("error getting uart frame")

def process_image_bytes(x_res, y_res, cpp, bpc, frame_data):
    #print(frame_data)
    #print(len(frame_data))
    image_bytes_list = uart_image_array_to_bytes(x_res, y_res, frame_data)
    image_bytes = bytes(image_bytes_list)
    new_image = pygame.image.frombuffer(image_bytes, size, 'RGB')
    screen.blit(new_image, (0,0))
    pygame.display.flip()

# def image_to_bytes(x_res, y_res, frame_data):
#     image_bytes_list = []
#     y = y_res
#     x = x_res
#     # while(y):
#     #     x = x_res
#     #     while(x):
#     #         image_bytes_list.append(0xff)
#     #         image_bytes_list.append(0xff)
#     #         image_bytes_list.append(0xff)
#     #         x = x - 1
#     #     y = y - 1
#     for data in frame_data:
#         data_word = int(data)
#         shifter = 0xffffffff
#         while(shifter):
#             if(data_word & 0x1):
#                 # bit is 1 - write in 
#                 #image_bytes_list.append(0xffffff)
#                 image_bytes_list.append(0xff)
#                 image_bytes_list.append(0xff)
#                 image_bytes_list.append(0xff)
#             else:
#                 #image_bytes_list.append(0x000000)
#                 image_bytes_list.append(0x00)
#                 image_bytes_list.append(0x00)
#                 image_bytes_list.append(0x00)
#             data_word = (data_word >> 1)
#             shifter = shifter >> 1
#             x = x - 1
#             if(x == 0):
#                 x = x_res
#                 y = y - 1
#                 if(y == 0):
#                     return image_bytes_list
#     return image_bytes_list

def uart_image_array_to_bytes(x_res, y_res, frame_data):
    image_bytes_list = []
    y = y_res
    x = x_res
    bytes_per_word = 1
    # while(y):
    #     x = x_res
    #     while(x):
    #         image_bytes_list.append(0xff)
    #         image_bytes_list.append(0xff)
    #         image_bytes_list.append(0xff)
    #         x = x - 1
    #     y = y - 1
    # pixel = 0
    # shifter = 0
    # bit_counter = 0
    # masked_data = 0
    y_counter = 0
    x_counter = 0
    index = 4
    while(y_counter < y_res):
        x_counter = 0
        while(x_counter < x_res):
            image_bytes_list.append(int(frame_data[index]))
            image_bytes_list.append(int(frame_data[index]))
            image_bytes_list.append(int(frame_data[index]))
            x_counter = x_counter + 1
            index = index + 1
        index = index + 4
        y_counter = y_counter + 1

    return image_bytes_list

def image_array_to_bytes(x_res, y_res, frame_data):
    image_bytes_list = []
    y = y_res
    x = x_res
    bytes_per_word = 1
    # while(y):
    #     x = x_res
    #     while(x):
    #         image_bytes_list.append(0xff)
    #         image_bytes_list.append(0xff)
    #         image_bytes_list.append(0xff)
    #         x = x - 1
    #     y = y - 1
    # pixel = 0
    # shifter = 0
    # bit_counter = 0
    # masked_data = 0
    y_counter = 0
    x_counter = 0
    index = 0
    while(y_counter < y_res):
        x_counter = 0
        while(x_counter < x_res):
            image_bytes_list.append(int(frame_data[index]))
            image_bytes_list.append(int(frame_data[index]))
            image_bytes_list.append(int(frame_data[index]))
            x_counter = x_counter + 1
            index = index + 1
        y_counter = y_counter + 1

    return image_bytes_list

def image_to_bytes(x_res, y_res, frame_data):
    image_bytes_list = []
    y = y_res
    x = x_res
    bytes_per_word = 1
    # while(y):
    #     x = x_res
    #     while(x):
    #         image_bytes_list.append(0xff)
    #         image_bytes_list.append(0xff)
    #         image_bytes_list.append(0xff)
    #         x = x - 1
    #     y = y - 1
    # pixel = 0
    # shifter = 0
    # bit_counter = 0
    # masked_data = 0
    for data in frame_data:
        data_word = int(data)
        counter = 0
        while(counter < bytes_per_word):
            image_data = data_word & 0x000000ff
            image_bytes_list.append(image_data)
            image_bytes_list.append(image_data)
            image_bytes_list.append(image_data)
            data_word = data_word >> 8
            counter = counter + 1

    return image_bytes_list
    # while(pixel < len(frame_data)):
    #     if(shifter == 0):
    #         data_word = int(frame_data[pixel])
    #         shifter = 0xffffffff
    #         pixel = pixel + 1
    #     masked_data = (data_word & 0xff)
    #     # masked_data = masked_data | (data_bit << bit_counter)
    #     data_word = (data_word >> 8)
    #     shifter = shifter >> 8
    #     image_bytes_list.append(masked_data)
    #     image_bytes_list.append(masked_data)
    #     image_bytes_list.append(masked_data)
    #     x = x - 1
    #     if(x == 0):
    #         x = x_res
    #         y = y - 1
    #         if(y == 0):
    #             return image_bytes_list
    #     # if(bit_counter == 6):
    #     #     bit_counter = 0
    #     #     masked_data = masked_data << 2
    #     #     image_bytes_list.append(masked_data)
    #     #     image_bytes_list.append(masked_data)
    #     #     image_bytes_list.append(masked_data)
    #     #     masked_data = 0
            
    #     # while(shifter):
    #         # masked_data = data_word & 0xff
            
    #         # if(data_word & 0x1):
    #         #     # bit is 1 - write in 
    #         #     #image_bytes_list.append(0xffffff)
    #         #     image_bytes_list.append(0xff)
    #         #     image_bytes_list.append(0xff)
    #         #     image_bytes_list.append(0xff)
    #         # else:
    #         #     #image_bytes_list.append(0x000000)
    #         #     image_bytes_list.append(0x00)
    #         #     image_bytes_list.append(0x00)
    #         #     image_bytes_list.append(0x00)
    #         # data_word = (data_word >> 6)
    #         # shifter = shifter >> 6
    return image_bytes_list


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