from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import FileResponse
import os
from scripts.blue_brown import generate_blue_brown_overlay
from scripts.dem_generator import generate_dem
from scripts.waterseg import flood_seg_yolo
from scripts.shortest_path import generate_shortest_path
from scripts.road_extraction import road_display
from scripts.gearth_image import generate_google_earth_image  # ✅ Import Google Earth generator
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS Setup to allow requests from React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now (can restrict to localhost later)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths to output images
DEM_PATH = "/Users/bbhavna/Desktop/final project code/backend/outputs/dem_map.png"
ROAD_PATH = "/Users/bbhavna/Desktop/final project code/backend/outputs/predicted_mask_cv.png"
BLUE_BROWN_PATH = "/Users/bbhavna/Desktop/final project code/backend/outputs/blue-brown roads.png"
PATH_RESULT = "/Users/bbhavna/Desktop/final project code/backend/outputs/shortest_path.png"
FLOOD_PATH = "/Users/bbhavna/Desktop/final project code/backend/outputs/floodoutput.jpg"
FILE_PATH = "/Users/bbhavna/Desktop/final project code/backend/path_lengths.txt"
PLACEDATA_PATH = "/Users/bbhavna/Desktop/final project code/backend/place_data.txt"

@app.post("/process/")
async def process_location(place: str = Form(...)):
    """Process location to generate DEM, road extraction, blue-brown overlay, shortest path, and Google Earth image."""
    print(f"✅ RECEIVED PLACE: {place}")

    # Step 1: Generate DEM
    dem_generated = generate_dem(place)
    if not dem_generated:
        raise HTTPException(status_code=400, detail="Error generating DEM.")
    
    # Step 2: Extract Roads
    road_extracted = road_display(ROAD_PATH, place)
    if not road_extracted:
        raise HTTPException(status_code=400, detail="Error extracting roads.")
    
    # Step 3: Generate Blue-Brown Overlay
    blue_brown_result = generate_blue_brown_overlay(DEM_PATH, ROAD_PATH, BLUE_BROWN_PATH)
    if not blue_brown_result:
        raise HTTPException(status_code=400, detail="Error generating blue-brown roads.")
    
    # ✅ Step 4: Get Google Earth Image Path
    gearth_result = generate_google_earth_image(place)
    if not gearth_result:
        raise HTTPException(status_code=404, detail=f"Google Earth image not found for {place}.")
    
    # Step 5: Generate Shortest Path
    path_result = generate_shortest_path(BLUE_BROWN_PATH, PATH_RESULT)
    if not path_result:
        raise HTTPException(status_code=400, detail="Error generating shortest path.")

    flood_extracted = flood_seg_yolo(place)
    if not flood_extracted:
        raise HTTPException(status_code=400, detail="Error extracting flood image.")
    
    # Return image paths for frontend
    return {
        "dem_path": DEM_PATH,
        "path_result": PATH_RESULT,
        "gearth_path": gearth_result , # ✅ Send Google Earth image path
        "waterseg":FLOOD_PATH
    }



@app.get("/get-data")
async def get_data():
    data_list = []
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r") as file:
            for line in file:
                path_number, path_length, time = line.strip().split(",")
                data_list.append({
                    "pathNumber": int(path_number),
                    "pathLength" : float(path_length.strip()),  # Correct way to handle decimals
                    "time": float(time)
                })
    return {"data": data_list}


@app.get("/get-place-data/{place_name}")
async def get_place_data(place_name: str):
    place_data = {}
    if os.path.exists(PLACEDATA_PATH):
        with open(PLACEDATA_PATH, "r") as file:
            for line in file:
                place_info = line.strip().split(",")
                if place_info[0].strip().lower() == place_name.lower():
                    place_data = {
                        "placeName": place_info[0],
                        "populationDensity": place_info[1],
                        "area": place_info[2],
                        "elevation": place_info[3],
                        "boatsNeeded": place_info[4]
                    }
                    break
    return place_data
    
@app.get("/get-dem")
async def get_dem():
    """Return DEM image."""
    if os.path.exists(DEM_PATH):
        return FileResponse(DEM_PATH, media_type="image/png")
    raise HTTPException(status_code=404, detail="DEM not found")

# Removed Blue-Brown endpoint as it's no longer needed

@app.get("/get-gearth/")
async def get_gearth(place: str):
    """Return Google Earth Image."""
    gearth_path = generate_google_earth_image(place)

    # Check if path is valid
    if gearth_path and os.path.exists(gearth_path):
        return FileResponse(gearth_path, media_type="image/jpg")
    
    # Return 404 if image not found
    raise HTTPException(status_code=404, detail=f"Google Earth image not found for {place}")

@app.get("/get-path")
async def get_path():
    """Return Shortest Path image."""
    if os.path.exists(PATH_RESULT):
        return FileResponse(PATH_RESULT, media_type="image/png")
    raise HTTPException(status_code=404, detail="Shortest path not found")

@app.get("/get-flood")
async def get_flood():
    """Return Flood Segmentation Image."""
    if os.path.exists(FLOOD_PATH):
        return FileResponse(FLOOD_PATH, media_type="image/jpg")  # ✅ Corrected media type
    raise HTTPException(status_code=404, detail="Flood image not found")
