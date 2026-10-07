IMPORTANT CORRECTION TO THE CURRENT IMPLEMENTATION

You have already implemented the SmartMetro computer vision pipeline with:
- YOLO person detection
- person tracking
- seated/standing classification
- seat occupancy
- density calculation
- telemetry
- Flask integration

However, the current implementation is NOT using the seat mapping concept we actually want.

The current output is incorrectly classifying people based on dynamically inferred/approximate regions.

DO NOT DELETE THE EXISTING WORK.

Modify the existing implementation so that seat detection/classification is based on FIXED, MANUALLY DEFINED SEAT POLYGONS.

============================================================
1. CORE REQUIREMENT
============================================================

The camera inside the metro compartment is FIXED.

Therefore:

THE PHYSICAL SEATS ARE FIXED RELATIVE TO THE CAMERA.

This means we know the image coordinates of every seat.

We will manually define the coordinates of the seats ONCE for a particular camera/coach configuration.

Example:

Seat S1:
[(100,300), (180,300), (190,380), (95,380)]

Seat S2:
[(180,300), (260,300), (270,380), (190,380)]

Seat S3:
[(300,300), (380,300), (390,380), (295,380)]

These polygons represent the actual physical seat locations in the camera's image.

The algorithm MUST NOT try to discover or guess where the seats are.

The algorithm MUST NOT use the current detected people to dynamically create seat regions.

The seat polygons are fixed configuration data.

============================================================
2. IMPORTANT DISTINCTION
============================================================

YOLO is responsible ONLY for:

PERSON DETECTION

The tracker is responsible for:

PERSON TRACKING

Our custom SmartMetro algorithm is responsible for:

PERSON → SEAT ASSOCIATION
SEATED/STANDING CLASSIFICATION
SEAT OCCUPANCY
TEMPORAL VERIFICATION
DENSITY CALCULATION

Do not claim that YOLO directly detects "seated" or "standing".

YOLO gives:

bbox + confidence + class

The seat mapping algorithm determines:

SEATED
STANDING
UNKNOWN

============================================================
3. SEAT CONFIGURATION
============================================================

Create a permanent configuration file.

For example:

backend/data/seat_config.json

Structure:

{
    "C1": {
        "S1": {
            "polygon": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        },
        "S2": {
            "polygon": [[x1,y1],[x2,y2],[x3,y2],[x4,y4]]
        }
    }
}

Prefer a simpler format if appropriate:

{
    "C1": {
        "S1": [[100,300],[180,300],[190,380],[95,380]],
        "S2": [[180,300],[260,300],[270,380],[190,380]]
    }
}

The configuration must support an arbitrary number of seats.

Do NOT hardcode the coordinates inside Python source code.

============================================================
4. SEAT MAPPING TOOL
============================================================

Keep/create a small tool that allows us to define seat polygons.

Example:

python tools/seat_mapper.py --source videos/coach.mp4

The tool should:

1. Load one reference frame.
2. Display the frame.
3. Let us click the corners of a seat.
4. Create the polygon.
5. Ask for the seat ID.
6. Save it to seat_config.json.
7. Repeat for all seats.

Example interaction:

Click 4 points
→ Enter seat ID: S1
→ polygon saved

Click 4 points
→ Enter seat ID: S2
→ polygon saved

etc.

The tool must also provide a visual verification mode.

Example:

python tools/seat_mapper.py --config backend/data/seat_config.json

The displayed frame should show:

S1 polygon
S2 polygon
S3 polygon
...

This allows us to verify that our manually defined seat coordinates match the actual physical seats.

============================================================
5. FIXED CAMERA ASSUMPTION
============================================================

The camera is mounted permanently inside one metro compartment.

Therefore the following relationship is fixed:

IMAGE COORDINATES
        ↓
PHYSICAL SEAT LOCATION

Example:

Image coordinate region:

        S1
   ┌──────────┐
   │          │
   │  SEAT    │
   │          │
   └──────────┘

The polygon does not move between frames.

Do NOT recalculate seat coordinates every frame.

Do NOT use YOLO to detect seats.

Do NOT use image segmentation to automatically discover seats.

Do NOT move the seat polygon according to the detected person.

============================================================
6. PERSON POSITION
============================================================

For every tracked person bounding box:

[x1, y1, x2, y2]

calculate:

bottom_center_x = (x1 + x2) / 2
bottom_center_y = y2

This bottom-center point represents the approximate contact/foot position of the person.

However, DO NOT use bottom-center as the ONLY condition.

Use it as the primary spatial reference and combine it with the person's bounding box relationship to the seat polygon.

============================================================
7. PERSON → SEAT MAPPING
============================================================

For every tracked person:

1. Calculate bottom-center point.

2. Test the point against every predefined seat polygon.

3. If the point lies inside a seat polygon, that seat becomes a CANDIDATE seat.

Example:

Person P1:

bottom-center = (145, 350)

Check:

P1 point inside S1?
YES

P1 point inside S2?
NO

P1 point inside S3?
NO

Therefore:

P1 → candidate S1

Do NOT immediately mark S1 occupied.

This is only a candidate association.

============================================================
8. IMPORTANT: SEATED VS STANDING
============================================================

A person should be classified as SEATED when:

- their tracked position is consistently associated with a predefined seat polygon
- the association remains stable for several consecutive frames
- the seat is not simultaneously assigned to another stable person

A person should be classified as STANDING when:

- they are confidently detected and tracked
- their position does not correspond to any predefined seat polygon
- they remain outside seat regions for the temporal verification window

UNKNOWN should be used when:

- detection confidence is too low
- the person is heavily occluded
- tracking is unstable
- the association cannot be determined reliably

============================================================
9. TEMPORAL VERIFICATION
============================================================

This is mandatory.

Do NOT classify a person as seated from one frame.

Example:

Frame 1:
P1 → candidate S1

Frame 2:
P1 → candidate S1

Frame 3:
P1 → candidate S1

Frame 4:
P1 → candidate S1

Frame 5:
P
|


run the demo on these images in the backend/demo_img section

and run those and lmk when done
