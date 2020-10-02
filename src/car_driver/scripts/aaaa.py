#! /usr/bin/env python
# encoding: utf-8
import rospy
import serial
import Queue
import threading
import struct
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu,MagneticField
## rosrun teleop_twist_keyboard teleop_twist_keyboard.py

def do_parse(ext_type,ext_len,ext_data):
    # 将ext_data 封装成完整的数据帧
    ext_data.insert(0, ext_len);
    ext_data.insert(0, ext_type);
    ext_data.insert(0, 0xfa);
    ext_data.insert(0,0xce);
    # CE FA 03 18    76 0E    5C 03 F0 FF 88 3C      E0 FF A2 00 84 00    00 A2 FF E0 00 84      F4 01     20 03
    # 根据数据帧的类型的类型来做对应的解析  0x01 线速度  0x02 电池
    if ext_type == 0x03:
        # 对数据进行拆包
        # 温度
        temperature = struct.unpack('h',bytearray(ext_data[4:6]))[0]

        # 加速度
        ax = struct.unpack('h',bytearray(ext_data[6:8]))[0]
        ay = struct.unpack('h',bytearray(ext_data[8:10]))[0]
        az = struct.unpack('h',bytearray(ext_data[10:12]))[0]
        # 角速度
        gx = struct.unpack('h', bytearray(ext_data[12:14]))[0]
        gy = struct.unpack('h', bytearray(ext_data[14:16]))[0]
        gz = struct.unpack('h', bytearray(ext_data[16:18]))[0]
        # 地磁
        mx = struct.unpack('h', bytearray(ext_data[18:20]))[0]
        my = struct.unpack('h', bytearray(ext_data[20:22]))[0]
        mz = struct.unpack('h', bytearray(ext_data[22:24]))[0]
        # 速度
        velocity = struct.unpack('h', bytearray(ext_data[24:26]))[0]
        angular = struct.unpack('h', bytearray(ext_data[26:28]))[0]

        # 发布陀螺仪的数据
        imu = Imu()
        # 根据芯片手册设定缩放系数
        accel_ratio = 1/16384.0
        imu.linear_acceleration.x = ax*accel_ratio;
        imu.linear_acceleration.y = ay*accel_ratio;
        imu.linear_acceleration.z = az*accel_ratio;

        # °/s 转成弧度/s
        gyro_ratio = 1/65.5/(180/3.1415926);
        imu.angular_velocity.x = gx*gyro_ratio;
        imu.angular_velocity.y = gy*gyro_ratio;
        imu.angular_velocity.z = gz*gyro_ratio;

        imuPublisher.publish(imu)

        # 发布地磁的数据
        mag = MagneticField();
        mag.magnetic_field.x = mx;
        mag.magnetic_field.y = my;
        mag.magnetic_field.z = mz;

        magPublisher.publish(mag);

        # print(velocity,angular)
        # 将小车当前的线速度和角速度发布出去
        twist = Twist()
        twist.linear.x = velocity/1000.0
        twist.angular.z = angular/1000.0
        velPublisher.publish(twist);




def do_recv():
    """
        找到一帧完整数据 从recv_queue中查找
        1. 查找帧头0
        2. 查找帧头1
        3. 查找帧类型
        4. 查找帧的长度
        5. 根据帧长度,读取帧数据
        完整的帧数据
    """
    while True:
        buff = recv_queue.get();
        value = bytearray(buff)[0]

        if value == 0xce: # 找到帧头0
            # 若找到帧头0,则继续判断帧头1
            value = bytearray(recv_queue.get())[0]
            if value == 0xfa: # 若判断成功,则head0和head1匹配成功,意味着帧头完全匹配
                # 开始读类型
                ext_type = bytearray(recv_queue.get())[0]
                # 读帧数据长度
                ext_len = bytearray(recv_queue.get())[0]
                # 读数据
                ext_data = []
                while len(ext_data) < ext_len:
                    # 不断往后读取数据
                    value = bytearray(recv_queue.get())[0]
                    ext_data.append(value);

                if ext_data[-1]== 0xad:
                    # 开始解析数据
                    do_parse(ext_type,ext_len,ext_data);


def cmd_vel_callback(msg):
    print("msg：",msg.linear.x,msg.angular.z);
    #     帧头0  帧头1  帧类型
    cmd = [0xce,0xfa,0x05]
    # 添加帧长度
    cmd.append(0x04);

    # 下发线速度和角速度
    velocity = msg.linear.x;
    angular = msg.angular.z;

    # 对数据进行拆解
    velocity_params = bytearray(struct.pack('h',int(velocity*1000)))
    angular_params = bytearray(struct.pack('h',int(angular*1000)))

    cmd.append(velocity_params[0])
    cmd.append(velocity_params[1])

    cmd.append(angular_params[0]);
    cmd.append(angular_params[1]);

    # [206, 250, 5, 4, 250, 0, 244, 1]
    # 将数据发送给串口
    ser.write(cmd)

##rosrun teleop_twist_keyboard teleop_twist_keyboard.py
if __name__ == '__main__':
    # 创建ros节点
    node_name="car_driver_node";
    rospy.init_node(node_name);

    # 订阅/cmd_vel
    rospy.Subscriber("/cmd_vel",Twist,cmd_vel_callback);
    # 发布者
    velPublisher = rospy.Publisher("/zxcar/get_vel",Twist,queue_size=50);
    # 发布陀螺仪的数据
    imuPublisher = rospy.Publisher("/zxcar/imu",Imu,queue_size=100);
    # 地磁的数据
    magPublisher = rospy.Publisher("/zxcar/magnetic",MagneticField,queue_size=50)

    port = rospy.get_param("~port", "/dev/ttyUSB0")

    # 创建serial 串口通讯对象
    ser = serial.Serial(port=port,baudrate=115200)

    # 判断串口是否打开成功
    if not ser.isOpen():
        ser.open();

    # 创建消息队列,专门用于存储读到的数据
    recv_queue = Queue.Queue();

    # 开启线程,专门用于取队列中查找帧数据
    threading.Thread(target=do_recv).start();
    try:
        # 读取串口中的数据
        while not rospy.is_shutdown():
            buff = ser.read();
            # 读到数据,立马存起来
            recv_queue.put(buff);
        rospy.spin();
    except Exception as e:
        rospy.logerr("car_driver:{}".format(e))
        ser.close();
        exit();


