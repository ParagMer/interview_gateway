from django.db import models

# class Trip(models.Model):
#     origin = models.CharField(max_length=255)
#     destination = models.CharField(max_length=255)
#     vehicle_type = models.CharField(max_length=50)
#     fuel_type = models.CharField(max_length=50)
#     load_weight = models.FloatField()
#     distance = models.FloatField()
#     terrain = models.CharField(max_length=50)
#     road_condition = models.CharField(max_length=50)
#     co2_emission = models.FloatField()
#     created_at = models.DateTimeField(auto_now_add=True)

# class TripSegment(models.Model):
#     trip = models.ForeignKey(Trip, related_name='segments', on_delete=models.CASCADE)
#     city = models.CharField(max_length=100)
#     distance = models.FloatField()     
#     terrain = models.CharField(max_length=50)  
#     road_type = models.CharField(max_length=50)
#     co2_emission = models.FloatField(null=True)
