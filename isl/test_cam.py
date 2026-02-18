
import cv2
import time

def test_cameras():
    print("OpenCV Version:", cv2.__version__)
    print("Testing cameras...")

    # Indices to check
    indices = [0, 1, 2, 3]
    # Backends to check
    backends = {
        'CAP_DSHOW': cv2.CAP_DSHOW,
        'CAP_MSMF': cv2.CAP_MSMF,
        'CAP_ANY': cv2.CAP_ANY
    }

    found = False

    for index in indices:
        print(f"\n--- Checking Camera Index {index} ---")
        for backend_name, backend_val in backends.items():
            print(f"  Trying backend {backend_name}...")
            cap = cv2.VideoCapture(index, backend_val)
            
            if cap.isOpened():
                print(f"    ✅ Camera opened successfully with {backend_name}!")
                
                # Try reading a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"    ✅ Frame captured successfully! Resolution: {frame.shape[1]}x{frame.shape[0]}")
                    found = True
                    cap.release()
                    break # Move to next index if one backend works, or continue? Let's just break this backend loop
                else:
                    print(f"    ❌ Camera opened but failed to capture frame.")
                cap.release()
            else:
                print(f"    ❌ Failed to open camera.")
    
    if not found:
        print("\nSUMMARY: No working cameras found on tried indices.")
    else:
        print("\nSUMMARY: Working camera(s) found.")

if __name__ == "__main__":
    test_cameras()
