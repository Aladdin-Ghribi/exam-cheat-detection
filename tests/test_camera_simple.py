import cv2

print("Testing camera access...")

# Try different camera indices
for i in range(3):
    print(f"\nTrying camera index {i}...")
    cap = cv2.VideoCapture(i)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ Camera {i} works! Resolution: {frame.shape[1]}x{frame.shape[0]}")
            cv2.imshow(f'Camera {i}', frame)
            cv2.waitKey(2000)
            cv2.destroyAllWindows()
        else:
            print(f"❌ Camera {i} opened but can't read frames")
        cap.release()
    else:
        print(f"❌ Camera {i} failed to open")

print("\nIf no camera worked, close all apps using the camera and try again.")
