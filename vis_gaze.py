import json
import cv2
import os

fold_dir:str = 'F:/bachelor_thesis/data/3d/pear_banana_in_sink/2025_07_03-13_15_54/sensors/continuous_device_'
files = sorted(os.listdir(fold_dir))

# get union of image and gaze files that have the same name, ignore the extension
paired_files = []
for f in files:
    if f.endswith('.png'):
        gaze_file = f.replace('.png', '.json')
        if gaze_file in files:
            paired_files.append(f.replace('.png', ''))
    
# sort paired files by their float value in the name
paired_files = sorted(paired_files, key=lambda x: int(x))

image_files = [os.path.join(fold_dir, f"{f}.png") for f in paired_files]
gaze_files = [os.path.join(fold_dir, f"{f}.json") for f in paired_files]

print(f'[INFO] found {len(image_files)} image files and {len(gaze_files)} gaze files'
      f' in {fold_dir}')

curr_idx = 0
break_flag = False
cv2.namedWindow('window', cv2.WINDOW_NORMAL)
# resize window to 16:9 aspect ratio
cv2.resizeWindow('window', 1280, 720)
while (curr_idx < len(paired_files) and break_flag is not True):
    image_file_path = image_files[curr_idx]
    image = cv2.imread(image_file_path)
    # rotate image 180 degrees
    image = cv2.rotate(image, cv2.ROTATE_180)

    gaze_file_path = gaze_files[curr_idx]
    gaze_pos_rel = json.load(open(gaze_file_path, 'r'))
    gaze_pos_abs = (gaze_pos_rel['x'] * image.shape[1],
                    (1 - gaze_pos_rel['y']) * image.shape[0])

    # draw gaze point
    cv2.circle(image, (int(gaze_pos_abs[0]), int(gaze_pos_abs[1])), 5, (0, 255, 0), -1)
    cv2.imshow('window', image)
    while True:
        key = cv2.waitKey(0)

        # d: next
        if key == 100:
            if curr_idx < len(image_files) - 1:
                curr_idx += 1
                print(f'[INFO] next {curr_idx} / {len(image_files)}')
            else:
                print(f'[WARN] already at the last image')
            break
        # a: previous 
        elif key == 97:
            if curr_idx > 0:
                curr_idx -= 1
                print(f'[INFO] previous {curr_idx} / {len(image_files)}')
                break
            else:
                print(f'[WARN] already at the first image')

        # esc or q: stop
        elif key == 27:
            print(f'[INFO] quit at {curr_idx}: {fold_dir}')
            cv2.destroyAllWindows()
            break_flag = True
            break
        # other: just log it.
        else:
            print(f'[WARN] input {key} unknown')