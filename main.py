import os
from Detection import ml_pipeline

IMAGE_FOLDER = "images"

def main():
    for img_name in os.listdir(IMAGE_FOLDER):
        img_path = os.path.join(IMAGE_FOLDER, img_name)
        
        print("\nProcessing:", img_name)
        
        result = ml_pipeline.process_image(img_path)
        
        print(result)

if __name__ == "__main__":
    main()