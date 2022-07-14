project_open project
puts "PLDUDE:BEGIN"
set op_arg [lindex $argv 0]
if { $op_arg == "hardware" } {
    foreach hardware [get_hardware_names] {
        puts $hardware;
    }
} elseif { $op_arg == "device" } {
    foreach device [get_device_names -hardware_name [lindex $argv 1]] {
        puts $device;
    }
}
puts "PLDUDE:END"