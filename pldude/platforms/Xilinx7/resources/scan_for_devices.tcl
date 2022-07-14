puts "PLDUDE:BEGIN"
foreach target [get_hw_targets] {
    current_hw_target $target;
    open_hw_target -quiet;
    puts -nonewline $target; puts -nonewline " ";
    puts [get_hw_devices -of_object [current_hw_target]];
    close_hw_target -quiet;
}
puts "PLDUDE:END"