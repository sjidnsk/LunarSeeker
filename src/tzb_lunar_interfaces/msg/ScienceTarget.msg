uint8 STATUS_UNKNOWN=0
uint8 STATUS_CANDIDATE=1
uint8 STATUS_CONFIRMED=2
uint8 STATUS_REJECTED=3
uint8 STATUS_COLLECTED=4

std_msgs/Header header
string target_id
string target_type
float32 confidence
geometry_msgs/PoseStamped pose
uint8 status
bool selected_for_sampling

