include <BOSL2/std.scad>

// size of the box, including all margins. Don't change the first two values without changing the slide size
box_size = [27, 79, 18];
// size of a single slide
slide_size = [25.2, 77, 1.25];

/* [Advanced] */

// chamfer on the outside of the box
outer_chamfer = 1; // 0.05
// chamfer on the inside of the box
inner_chamfer = 0.8; // 0.05
// wall strength
wall_strength = 1.5; // 0.05
// minimum length for a slot in the walls
slot_length_min = 10; // 1
// width of a slot (make sure your desiccant is larger than this)
slot_width = 1; // 0.05
// minimum distance between slots
slot_spacing_min = 1.5; // 0.05
// size of the lip above the slide that holds it in place
slide_lip = 1; // 0.05
// size of the slot at the end of the slide lip, for pushing the slide back out
slide_grab = 10; // 1
// size of the retainer lip at the end of the box
retainer_size = [10, 0.7, 0.4]; // 0.05
// divot next to the retainer, for grabbing the slide
divot_depth = 0.75; // 0.05
// section of the lip that is cleared entirely. This allows you to grab the slide from the side
clear_length = 0; // 1
// section of the lip that does not have the top retention part, allowing the slide to bend upwards but still protecting the slide edges and corner from chipping
guarded_length = 35; // 1

$fn = 50;

module slot(length) {
    hull() {
        translate([0, (length - slot_width) / 2]) circle(d=slot_width);
        translate([0, -(length - slot_width) / 2]) circle(d=slot_width);
    }
}

function fit_slots(size, item_size) = floor((size - slot_spacing_min) / (item_size + slot_spacing_min));

module wall_cutouts(size) {
    num_slots = [
        fit_slots(size.x, slot_width),
        fit_slots(size.y, slot_length_min)
    ];
    slot_spacing = [
        (size.x - slot_width * num_slots.x) / (num_slots.x + 1),
        slot_spacing_min
    ];
    assert(slot_spacing.x >= slot_spacing_min);
    slot_length = (size.y - slot_spacing_min * (num_slots.y + 1)) / num_slots.y;
    assert(slot_length >= slot_length_min);
    translate(-size/2) for (ix = [0:num_slots.x-1]) for (iy = [0:num_slots.y-1]) {
        translate([
            (ix + 1) * slot_spacing.x + (ix + 0.5) * slot_width,
            (iy + 1) * slot_spacing.y + (iy + 0.5) * slot_length
        ]) slot(slot_length);
    }
}

module box() {
    wall_v = [wall_strength, wall_strength, wall_strength];
    difference() {
        cuboid(box_size, chamfer=outer_chamfer);
        cuboid(box_size - wall_v * 2, chamfer=inner_chamfer);
        translate([-slide_size.x / 2, box_size.y / 2, box_size.z / 2 - slide_size.z - slide_lip]) {
            rotate([90, 0, 0]) {
                linear_extrude(slide_size.y + retainer_size.y) polygon([
                    [0, 0],
                    [0, slide_size.z],
                    [slide_lip, slide_size.z + slide_lip],
                    [slide_size.x - slide_lip, slide_size.z + slide_lip],
                    [slide_size.x, slide_size.z],
                    [slide_size.x, 0],
                ]);
                translate([-(box_size.x - slide_size.x) / 2, 0, guarded_length]) linear_extrude(clear_length) square([box_size.x, slide_size.z + slide_lip]);
                linear_extrude(guarded_length) square([slide_size.x, slide_size.z + slide_lip]);
            }
        }
        translate([-slide_grab / 2, -box_size.y / 2, box_size.z / 2]) {
            rotate([-90, 0, 0]) cube([slide_grab, slide_size.z + slide_lip, box_size.y - slide_size.y]);
        };
        adj_size = [
            box_size.x - wall_strength*2,
            box_size.y - wall_strength*2,
            box_size.z - wall_strength - slide_lip - slide_size.z
        ];
        z_adj = slide_lip + slide_size.z - wall_strength;
        translate([0, 0, -box_size.z / 2]) linear_extrude(wall_strength) wall_cutouts([adj_size.x, adj_size.y]);
        translate([box_size.x / 2, 0, -z_adj]) rotate([90, 0, 0]) rotate([0, -90, 0]) linear_extrude(wall_strength) wall_cutouts([adj_size.y, adj_size.z]);
        translate([-box_size.x / 2, 0, -z_adj]) rotate([90, 0, 0]) rotate([0, 90, 0]) linear_extrude(wall_strength) wall_cutouts([adj_size.y, adj_size.z]);
        translate([0, box_size.y / 2, -z_adj]) rotate([90, 0, 0]) linear_extrude(wall_strength) wall_cutouts([adj_size.x, adj_size.z]);
        translate([0, -box_size.y / 2, -z_adj]) rotate([-90, 0, 0]) linear_extrude(wall_strength) wall_cutouts([adj_size.x, adj_size.z]);
        translate([-slide_size.x / 2 + retainer_size.x, box_size.y / 2 - wall_strength - inner_chamfer, box_size.z / 2 - slide_size.z - slide_lip - divot_depth]) cube([box_size.x - wall_strength * 2 - retainer_size.x - inner_chamfer, wall_strength + inner_chamfer, divot_depth * 2]);
    }
    translate([-slide_size.x / 2, box_size.y / 2 - retainer_size.y, box_size.z / 2 - slide_size.z - slide_lip]) {
        cube(retainer_size);
    };
}

box();
