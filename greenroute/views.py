import os, requests, folium, json, polyline
from google import genai
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from geopy.distance import geodesic
from simplification.cutil import simplify_coords
from collections import OrderedDict
from .config import *

client = genai.Client(api_key=GEMINI_KEY)

@method_decorator(csrf_exempt, name='dispatch')
class CalculateEmissions(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        vehicle_type = data.get("vehicle_type")
        fuel_type = data.get("fuel_type")
        segments = data.get("segments", [])

        if not all([vehicle_type, fuel_type, segments]):
            return JsonResponse({"error": "Missing required inputs: vehicle_type or fuel_type or segments"}, status=400)

        results = []
        total_ttw = total_wtt = 0.0

        for seg in segments:
            try:
                city = seg["city"]
                distance_km = float(seg["distance"])           # in km
                load_weight_ton = float(seg["load_weight"])    # in tons
                terrain = seg["terrain"]
                road_type = seg["road_type"]
            except (KeyError, ValueError):
                return JsonResponse({"error": "Invalid segment data"}, status=400)

            emissions = calculate_emissions(vehicle_type, fuel_type, load_weight_ton, distance_km, terrain, road_type)
            total_ttw += emissions["TTW"]
            total_wtt += emissions["WTT"]

            results.append({"city": city,"distance_km": round(distance_km, 2),"load_weight_ton": load_weight_ton, "TTW_kg": emissions["TTW"], "WTT_kg": emissions["WTT"], "WTW_kg": emissions["WTW"]})
        
        return JsonResponse({"vehicle_type": vehicle_type, "fuel_type": fuel_type,"results": results,"total_TTW_kg": round(total_ttw, 2), "total_WTT_kg": round(total_wtt, 2), "total_WTW_kg": round(total_ttw + total_wtt, 2)})

@method_decorator(xframe_options_exempt, name='dispatch')
class ViewMap(View):
    def get(self, request, *args, **kwargs):
        return render(request, "html/route_map.html")

@method_decorator(csrf_exempt, name='dispatch')
class RouteFollow(View):
    def get(self, request, *args, **kwargs):
        return render(request, "html/home.html")

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
            start = body.get("start")
            end = body.get("end")
            vehicle_type = body.get("vehicle_type")
            fuel_type = body.get("fuel_type")
            load_weight_ton = int(body.get("load_weight_ton"))
            road_type = body.get("road_type")
            terrain = body.get("terrain")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if not start or not end or not vehicle_type:
            return JsonResponse({"error": "start, end, and vehicle_type are required."}, status=400)

        if vehicle_type.lower() != "walk":
            if not all([fuel_type, load_weight_ton, road_type, terrain]):
                return JsonResponse({"error": "fuel_type, load_weight_ton, road_type, and terrain are required."}, status=400)


        travel_mode = travel_mode_map.get(vehicle_type.lower(), "DRIVE")
        google_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_API_KEY,
            # "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.routeLabels,routes.legs"
        }

        payload = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": float(start.split(',')[0]),
                        "longitude": float(start.split(',')[1])
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": float(end.split(',')[0]),
                        "longitude": float(end.split(',')[1])
                    }
                }
            },
            "travelMode": travel_mode
        }

        response = requests.post(google_url, headers=headers, json=payload)
        google_data = response.json()

        if "routes" not in google_data or not google_data["routes"]:
            return JsonResponse({"error": "No route found", "details": google_data}, status=500)

        route = google_data["routes"][0]
        encoded_polyline = route['polyline']['encodedPolyline']
        coordinates = polyline.decode(encoded_polyline)
        decoded = polyline.decode(encoded_polyline)

        simplified_coords = simplify_coords(decoded, epsilon=0.0008)

        # Limit to max 50 if still too many
        if len(simplified_coords) > 50:
            step = len(simplified_coords) // 50
            simplified_coords = [simplified_coords[i] for i in range(0, len(simplified_coords), step)]
            if simplified_coords[-1] != decoded[-1]:
                simplified_coords.append(decoded[-1])

        coordinates = simplified_coords
        # Draw map
        start_coords = [float(start.split(',')[0]), float(start.split(',')[1])]
        end_coords = [float(end.split(',')[0]), float(end.split(',')[1])]
        route_map = folium.Map(location=start_coords, zoom_start=14)
        folium.PolyLine(locations=coordinates, color="blue").add_to(route_map)
        folium.Marker(location=start_coords, tooltip="Start").add_to(route_map)
        folium.Marker(location=end_coords, tooltip="End").add_to(route_map)

        output_path = os.path.join("templates", "html", "route_map.html")
        route_map.save(output_path)

        city_segments = OrderedDict()
        total_ttw = total_wtt = 0.0
        cumulative_distance_km = 0.0
        last_point = coordinates[0]
        visited_cities = set()

        for i in range(1, len(coordinates)):
            point = coordinates[i]
            segment_distance_km = geodesic(last_point, point).km
            cumulative_distance_km += segment_distance_km
            lat, lon = point
            city = get_city_name(lat, lon)

            emissions = calculate_emissions(vehicle_type, fuel_type, load_weight_ton, segment_distance_km, terrain, road_type)
            ttw = emissions.get("TTW", 0.0)
            wtt = emissions.get("WTT", 0.0)

            total_ttw += ttw
            total_wtt += wtt

            if city not in visited_cities:
                visited_cities.add(city)

                city_segments[city] = {
                    "distance_km": round(cumulative_distance_km, 2),
                    "TTW_kg": round(total_ttw, 2),
                    "WTT_kg": round(total_wtt, 2),
                    "WtW_kg": round(total_ttw + total_wtt, 2)
                }

            last_point = point

        city_breakdown = [
            {
                "city": city,
                "distance_km": round(data["distance_km"], 2),
                "TTW_kg": round(data["TTW_kg"], 2),
                "WTT_kg": round(data["WTT_kg"], 2),
                "WtW_kg": round(data["WtW_kg"], 2)
            }
            for city, data in city_segments.items()
        ]

        distance_km = route.get("distanceMeters")/1000
        if vehicle_type.lower() == 'flight':
            duration_hours = distance_km / 800
        else:
            duration_hours = int(route.get("duration").replace('s', ''))/3600
        
        
        return JsonResponse({"start": start,"end": end, "distance_km": distance_km, "duration_hours": duration_hours,"TTW_kg": round(total_ttw, 2), "WTT_kg": round(total_wtt, 2), "WtW_kg": round(total_ttw + total_wtt, 2), "city_breakdown": city_breakdown})
        
@method_decorator(csrf_exempt, name='dispatch')
class CompareFuels(View):
    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
            baseline_fuel = body.get("baseline_fuel").lower()
            baseline_emission = float(body.get("baseline_emission"))
        except Exception as e:
            return JsonResponse({"error": "Invalid input", "details": str(e)}, status=400)

        baseline_factor = compare_emission_factors[baseline_fuel]
        comparisons = {}
        for fuel, factor in compare_emission_factors.items():
            if fuel == baseline_fuel:
                continue
            equivalent_emission = round(baseline_emission * (factor / baseline_factor), 2)
            diff = round(equivalent_emission - baseline_emission, 2)
            percent = round((diff / baseline_emission) * 100, 2)

            comparisons[fuel] = {
                "emission_kg": equivalent_emission,
                "diff_kg": f"{'+' if diff >= 0 else ''}{diff}",
                "percent": f"{'+' if percent >= 0 else ''}{percent}%"
            }
        return JsonResponse({"baseline": baseline_fuel, "baseline_emission": baseline_emission, "comparisons": comparisons})

@method_decorator(csrf_exempt, name='dispatch')
class GenerateReason(View):
    def post(self, request, *args, **kwargs):
        body = json.loads(request.body)
        response = client.models.generate_content(model="gemini-2.5-flash", contents=body['prompt'])
        return JsonResponse({"message": response.text})