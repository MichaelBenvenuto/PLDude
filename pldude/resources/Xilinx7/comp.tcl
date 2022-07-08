set part [lindex $argv 0]
set top [lindex $argv 1]
set is2008 [lindex $argv 2]

puts "PLDUDE: Creating project..."
create_project -in_memory -part $part

if { $is2008 == "True" } {
    set_property enable_vhdl_2008 1 [current_project]
}

foreach file_str [lrange $argv 3 end] {
    set arg_sanit [string range $file_str 1 end-1]
    set arg_split [split $arg_sanit \;]
    set op_arg [lindex $arg_split 0]
    
    if { $op_arg == "FILE" } {
        set ftype [lindex $arg_split 1]
        set fdir [lindex $arg_split 2]

        if { $ftype == "VHDL" } {
            if { $is2008 == "True" } {
                read_vhdl -vhdl2008 $fdir
            } elseif { $is2008 == "False" } {
                read_vhdl $fdir
            }
        } elseif { $ftype == "VERILOG"} {
            read_verilog $fdir
        }
    }
}

puts "PLDUDE: Running synthesis..."
synth_design -flatten_hierarchy none -top $top -part $part
opt_design -retarget -propconst -bram_power_opt -verbose

puts "PLDUDE: Running place and route..."

set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]

foreach file_str [lrange $argv 3 end] {
    set arg_sanit [string range $file_str 1 end-1]
    set arg_split [split $arg_sanit \;]
    set op_arg [lindex $arg_split 0]
    if { $op_arg == "IO" } {
        set ioprt [lindex $arg_split 1]
        set iopkg [lindex $arg_split 2]
        set iostd [lindex $arg_split 3]
        
        set_property -dict "PACKAGE_PIN $iopkg IOSTANDARD $iostd" [get_ports $ioprt]
    }
}

place_design
route_design -directive Explore

puts "PLDUDE: Running bitstream generation..."
write_bitstream -force ./bitfile/project.bit