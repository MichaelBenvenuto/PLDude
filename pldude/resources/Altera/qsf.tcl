project_new -family [get_part_info -family [lindex $argv 0]] -part [lindex $argv 0] -overwrite project
set_global_assignment -name TOP_LEVEL_ENTITY [lindex $argv 1]

foreach pin_str [lrange $argv 2 end] {
    set pin_split [split $pin_str \;]
    set op_arg [lindex $pin_split 0]
    puts $op_arg
    if { $op_arg == "FILE" } {
        set ftype [lindex $pin_split 1]_FILE
        set_global_assignment -name $ftype [lindex $pin_split 2]
    } elseif { $op_arg == "IO" } {
        set pin_loc PIN_[lindex $pin_split 2]
        set pin_virt [lindex $pin_split 1]
        set pin_std \"[lindex $pin_split 3]\"
        set_instance_assignment -name IO_STANDARD -to $pin_virt $pin_std
        set_location_assignment $pin_loc -to $pin_virt
    }
}

project_close