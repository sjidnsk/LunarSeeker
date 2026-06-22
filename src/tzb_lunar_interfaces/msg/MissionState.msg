uint8 PHASE_IDLE=0
uint8 PHASE_READY=1
uint8 PHASE_DEPARTURE=2
uint8 PHASE_EXPLORATION=3
uint8 PHASE_APPROACH=4
uint8 PHASE_SAMPLE=5
uint8 PHASE_RETURN=6
uint8 PHASE_UNLOAD=7
uint8 PHASE_COMPLETE=8
uint8 PHASE_FAULT=255

std_msgs/Header header
uint8 phase
string phase_name
uint16 collected_count
int32 estimated_score
float32 remaining_time_sec
uint16 fault_code
string fault_text
bool remote_intervention_detected

