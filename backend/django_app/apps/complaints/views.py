from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Complaint
from .serializers import ComplaintCreateSerializer, ComplaintSerializer


class ComplaintListCreateAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "complaints"

    def get(self, request):
        queryset = Complaint.objects.filter(reporter=request.user).order_by("-created_at")
        serializer = ComplaintSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ComplaintCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save()
        output = ComplaintSerializer(complaint)
        return Response(output.data, status=status.HTTP_201_CREATED)