from PIL import Image
import numpy as np

if __name__ == "__main__":
    # We will process the ORIGINAL logo again
    input_path = "assets/logo.png"
    output_path = "assets/logo_white_text.png"
    
    print(f"Processing {input_path}...")
    try:
        img = Image.open(input_path).convert("RGBA")
        data = np.array(img)
        
        # 1. Remove White Background (Threshold > 240)
        # Note: data shape is (H, W, 4), r/g/b/a shapes are (H, W) or (W, H) depending on how we unpack.
        # unpacking data.T gives (W, H) arrays.
        # Let's avoid .T unpacking which confuses shapes.
        
        r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
        
        white_bg = (r > 240) & (g > 240) & (b > 240)
        data[..., 3][white_bg] = 0
        
        # 2. Invert Black Text to White (Threshold < 50)
        dark_pixels = (r < 50) & (g < 50) & (b < 50) & (data[..., 3] > 0)
        
        data[..., 0][dark_pixels] = 255
        data[..., 1][dark_pixels] = 255
        data[..., 2][dark_pixels] = 255
        
        # Save
        new_img = Image.fromarray(data)
        new_img.save(output_path)
        print(f"Saved inverted logo to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
