import json
import cv2
import os
from alive_progress import alive_bar
import imageio
from PIL import Image 

# def enumerate_step(xs, start=0, step=1):
#     a = zip(range(len(xs), start, step), xs)
#     b = list(a)
#     return a

# traj_dir:str = os.path.join('F:', 'bachelor_thesis', 'data', '3d', 'tower', '2025_07_03-12_01_07', 'sensors', 'continuous_device_')
_source_dir = os.path.join('F:', 'bachelor_thesis', 'data', '3d')
_target_dir = os.path.join('F:', 'bachelor_thesis', 'gif', '3d')
skip_amount: int = 10

if not os.path.exists(_source_dir):
    print(f'[ERROR] directory {_source_dir} does not exist, exiting')
    exit(1)
if not os.path.exists(_target_dir):
    print(f'[INFO] target directory {_target_dir} does not exist, creating it')
    os.makedirs(_target_dir)

task_dir = os.listdir(_source_dir)
if len(task_dir) == 0:
    print(f'[ERROR] no task directories found in {_source_dir}, exiting')
    exit(1)

traj_src_dir = []
traj_target_dir = []

for task in task_dir:
    task_dir = os.path.join(_source_dir, task)
    if not os.path.isdir(task_dir):
        print(f'[WARN] {task_dir} is not a directory, skipping')
        continue
    
    for idx, traj_folder in enumerate(os.listdir(task_dir)):
        traj_dir = os.path.join(task_dir, traj_folder, "sensors", "continuous_device_")
        if not os.path.isdir(traj_dir):
            print(f'[WARN] {traj_dir} is not a directory, skipping')
            continue

        target_dir = os.path.join(_target_dir, task, f"{traj_folder}.gif")
        if os.path.exists(target_dir):
            print(f'[WARN] target file {target_dir} already exists, skipping')
            continue
        traj_target_dir.append(target_dir)
        traj_src_dir.append(traj_dir)

print(f'[INFO] found {len(traj_src_dir)} trajectories to process')
with alive_bar(len(traj_src_dir), title='Processing trajectories') as bar:
    for traj_dir, target_dir in zip(traj_src_dir, traj_target_dir):
        bar.text(f'Processing {traj_dir} -> {target_dir}')
        bar()


        files = sorted(os.listdir(traj_dir))

        # get union of image and gaze files that have the same name, ignore the extension
        paired_files = []
        for f in files:
            if f.endswith('.png'):
                gaze_file = f.replace('.png', '.json')
                if gaze_file in files:
                    paired_files.append(f.replace('.png', ''))
            
        # sort paired files by their float value in the name
        paired_files = sorted(paired_files, key=lambda x: int(x))

        image_files = [os.path.join(traj_dir, f"{f}.png") for f in paired_files]
        gaze_files = [os.path.join(traj_dir, f"{f}.json") for f in paired_files]

        print(f'[INFO] found {len(image_files)} image files and {len(gaze_files)} gaze files'
            f' in {traj_dir}')

        # create gif from images and gaze points
        
        target_folder = os.path.dirname(target_dir)
        if not os.path.exists(target_folder):
            print(f'[INFO] target folder {target_folder} does not exist, creating it')
            os.makedirs(target_folder)
        with imageio.get_writer(target_dir, mode='I') as writer:
            palette = None
            for i in range(0, len(image_files), skip_amount):
                image_file_path = image_files[i]
                gaze_file_path = gaze_files[i]
                image = cv2.imread(image_file_path)
                # rotate image 180 degrees
                image = cv2.rotate(image, cv2.ROTATE_180)

                gaze_pos_rel = json.load(open(gaze_file_path, 'r'))
                gaze_pos_abs = (gaze_pos_rel['x'] * image.shape[1],
                                (1 - gaze_pos_rel['y']) * image.shape[0])

                # draw gaze point
                cv2.circle(image, (int(gaze_pos_abs[0]), int(gaze_pos_abs[1])), 5, (0, 0, 255), -1)
                image_coverted = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                # # Displaying the converted image
                # pil_image = Image.fromarray(image_coverted)
                # if i == 0: # Quantize the first frame and get the palette
                #     pil_image = pil_image.quantize(colors=254, method=Image.Quantize.MAXCOVERAGE)
                #     palette = pil_image
                # else: # Quantize all other frames to the same palette
                #     pil_image = pil_image.quantize(colors=254, palette=palette, method=Image.Quantize.MAXCOVERAGE)
                writer.append_data(image_coverted)

        # while (curr_idx < len(paired_files) and break_flag is not True):
        #     image_file_path = image_files[curr_idx]
        #     image = cv2.imread(image_file_path)
        #     # rotate image 180 degrees
        #     image = cv2.rotate(image, cv2.ROTATE_180)

        #     gaze_file_path = gaze_files[curr_idx]
        #     gaze_pos_rel = json.load(open(gaze_file_path, 'r'))
        #     gaze_pos_abs = (gaze_pos_rel['x'] * image.shape[1],
        #                     gaze_pos_rel['y'] * image.shape[0])

        #     # draw gaze point
        #     cv2.circle(image, (int(gaze_pos_abs[0]), int(gaze_pos_abs[1])), 5, (0, 255, 0), -1)