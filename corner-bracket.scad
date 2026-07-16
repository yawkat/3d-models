include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

// size of the bracket. 30mm for 3030 extrusion, 20mm for 2020 extrusion etc.
size = 30;
// chamfer.
chamfer = 1;

// main diameter of the screw, 6.3 for M6.
screw_diameter = 6.3;
// how far the body of the screw (excluding the head!) will stick out of the extrusion. in other words, the distance of the screw head to the extrusion.
screw_depth = 3;
// diameter of the screw head.
counterbore_diameter = 11;

$fn=64;

module screw() {
    cylinder(h = screw_depth, d = screw_diameter);
    translate([0, 0, screw_depth]) cylinder(h=size, d=counterbore_diameter);
}

//rotate([-90, 0, 0])
//rotate([0, 0, 45])
//translate([-size / 2, -size / 2, -size / 2])
difference() {
    offset_sweep(
        path = round_corners([[0, 0], [size, 0], [0, size]], method="chamfer", cut=chamfer),
        height = size,
        bottom = os_chamfer(width = chamfer),
        top = os_chamfer(width = chamfer)
    );
    translate([size/2, 0, size/2]) rotate([-90, 0, 0]) screw();
    translate([0, size/2, size/2]) rotate([0, 90, 0]) screw();
}
