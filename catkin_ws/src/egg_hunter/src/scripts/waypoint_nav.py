#!/usr/bin/env python
import rospy
import actionlib
import math
from geometry_msgs.msg import Pose, PoseStamped, PoseWithCovarianceStamped
from move_base_msgs.msg	import MoveBaseGoal, MoveBaseAction
from visualization_msgs.msg import MarkerArray, Marker

class WaypointNav(object):
    def __init__(self):
        #I think this whole thing should happen in global. Have to look at SMACH implementation to be sure, that init happens only once.
        #Update. Yes, init does happen only once. Execute happens multiple times.
        self.waypoints = []
        self.waypoint_index = None

        rospy.init_node('waypoint_nav')
        waypoint_arr = rospy.get_param('/patrolling/waypoints')
        rospy.loginfo('Printing arr:: %s', waypoint_arr)
        rospy.loginfo('Length of array:: %2f',len(waypoint_arr)-1 )

        for wp in waypoint_arr:
            temp = MoveBaseGoal()

            rospy.loginfo('wp[0]::%2f', wp[0])
            rospy.loginfo('wp[1]::%2f', wp[1])
            rospy.loginfo('wp[2]::%2f', wp[2])
            rospy.loginfo('wp[3]::%2f', wp[3])

            temp.target_pose.header.frame_id = 'map'
            temp.target_pose.pose.position.x = wp[0]
            temp.target_pose.pose.position.y = wp[1]
            temp.target_pose.pose.orientation.z = wp[2]
            temp.target_pose.pose.orientation.w = wp[3]

            self.waypoints.append(temp)

            #Guessing everything from this point on goes into execute

        self.mvbs = actionlib.SimpleActionClient('move_base', MoveBaseAction)

        self.goal_sub = rospy.Subscriber("move_base_simple/goal", PoseStamped,
                                         self._update_waypoints) #This callback should connect to camera and take a picture. Switch states here.

        self.amcl_sub = rospy.Subscriber("amcl_pose", PoseWithCovarianceStamped,
                                         self._nearest_waypoint)

        self.viz_pub = rospy.Publisher("patrolling/viz_waypoints_array",
                                       MarkerArray, queue_size=10)
        self._publish_markers()

        rospy.loginfo("Waypoint Nav ready.")

    def _nearest_waypoint(self, pose):
        if not self.waypoint_index:
            shortest_len = float('inf')
            shortest_len_index = 0
            x = pose.pose.pose.position.x
            y = pose.pose.pose.position.y

            for i, wp in enumerate(self.waypoints):
                test_len = math.hypot(wp.target_pose.pose.position.x - x,
                                      wp.target_pose.pose.position.y - y)
                if test_len < shortest_len:
                    shortest_len = test_len
                    shortest_len_index = i

            self.waypoint_index = shortest_len_index

    def _update_waypoints(self, data):
        latest = MoveBaseGoal(target_pose = data)

        if rospy.get_param('/waypoints_nav/patrolling/update_patrol'):
            self.waypoints.insert(self.waypoint_index, latest)

            if rospy.get_param('/waypoints_nav/patrolling/save_latest'):
                ros.set_param_raw('/waypoints_nav/patrolling/waypoints',
                                  self.waypoints)

    def _publish_markers(self):
        markers = []
        for i, wp in enumerate(self.waypoints):
            temp = Marker()

            temp.header = wp.target_pose.header
            temp.id = i
            temp.ns = "patrolling"
            temp.action = Marker.ADD

            temp.type = Marker.ARROW
            temp.pose = wp.target_pose.pose
            temp.scale.x = 0.6
            temp.scale.y = 0.3
            temp.scale.z = 0.3
            temp.color.a = 1
            temp.color.r = 0
            temp.color.g = 0.5
            temp.color.b = 0.5
            markers.append(temp)
        self.viz_pub.publish(markers=markers)

        rospy.loginfo("Markers Published")
    #Navigation happens here
    def start_nav(self):
        self.mvbs.wait_for_server()
        forward = True

        rospy.wait_for_message("amcl_pose", PoseWithCovarianceStamped)

        rospy.loginfo("Nearest waypoint is #{}".format(self.waypoint_index))

        while not rospy.is_shutdown():
            rospy.loginfo(self.waypoint_index)
            rospy.loginfo(self.waypoints[self.waypoint_index])

            self._publish_markers()

            self.mvbs.send_goal(self.waypoints[self.waypoint_index])
            self.mvbs.wait_for_result()
            rospy.loginfo("Nav goal met, setting another one...")

            if self.waypoint_index >= len(self.waypoints) - 1:
                forward = False
            elif self.waypoint_index <= 0:
                forward = True

            if forward:
                self.waypoint_index = self.waypoint_index + 1
            else:
                self.waypoint_index = self.waypoint_index - 1

if __name__ == "__main__":
    WaypointNav().start_nav()
