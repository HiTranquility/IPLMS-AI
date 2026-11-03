"""gRPC transport for Admin model profiles."""
from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.model_policy_mapper import (
    to_create_profile_command, to_model_profile_response,
)
from app.core.model_policy import model_policy_service

_pb2, _pb2_grpc = get_stub("model_policy_service")


class ModelPolicyHandler(_pb2_grpc.ModelPolicyServiceServicer):
    async def ListProfiles(self, request, context):
        profiles = await model_policy_service.list_profiles()
        return _pb2.ListModelProfilesResponse(
            profiles=[to_model_profile_response(profile) for profile in profiles]
        )

    async def CreateProfile(self, request, context):
        profile = await model_policy_service.create_profile(
            to_create_profile_command(request), request.actor_id,
        )
        return to_model_profile_response(profile)

    async def TestProfile(self, request, context):
        return to_model_profile_response(await model_policy_service.test_profile(request.id))

    async def ActivateProfile(self, request, context):
        return to_model_profile_response(
            await model_policy_service.activate(request.id, request.actor_id)
        )
