from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from extensions.common.base import *
from extensions.common.schema import *
from extensions.common.schema import *
from extensions.common.base import *
from extensions.permissions import *
from extensions.exceptions import *
from extensions.viewsets import *
from apps.system.serializers import *
from apps.system.schemas import *
from apps.system.models import *


class UserViewSet(ModelViewSet):
    """用户"""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['username', 'name']
    ordering_fields = ['id', 'username', 'name']
    queryset = User.objects.all()

    def perform_destroy(self, instance):
        if instance.is_manager:
            raise ValidationError('无法删除管理员账号')

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(f'用户[{instance.username}]已被引用, 无法删除')

    @extend_schema(request=None, responses={200: None})
    @action(detail=True, methods=['post'])
    def reset_password(self, request, *args, **kwargs):
        """重置密码"""

        instance = self.get_object()
        instance.password = make_password('123456')
        instance.save(update_fields=['password'])

        return Response(status=status.HTTP_200_OK)


class UserActionViewSet(FunctionViewSet):
    """用户操作"""

    @extend_schema(request=GetTokenRequest, responses={200: GetTokenResponse})
    @action(detail=False, methods=['post'])
    def get_token(self, request, *args, **kwargs):
        """获取令牌"""

        serializer = GetTokenRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if not (user := User.objects.filter(team__number=validated_data['number'],
                                            username=validated_data['username']).first()):
            raise ValidationError('用户不存在')

        if not check_password(validated_data['password'], user.password):
            raise AuthenticationFailed('密码错误')

        token = RefreshToken()
        token['user_id'] = user.id
        data = {'refresh': str(token), 'access': str(token.access_token)}

        return Response(data=data, status=status.HTTP_200_OK)

    @extend_schema(request=RefreshTokenRequest, responses={200: RefreshTokenResponse})
    @action(detail=False, methods=['post'])
    def refresh_token(self, request, *args, **kwargs):
        """刷新令牌"""

        serializer = RefreshTokenRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        try:
            token = RefreshToken(validated_data['refresh'])
        except TokenError:
            raise NotAuthenticated('令牌失效')

        data = {'access': str(token.access_token)}
        return Response(data=data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: UserInfoResponse})
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def info(self, request, *args, **kwargs):
        """用户信息"""

        serializer = UserInfoResponse(instance=self.user)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=SetPasswordRequest, responses={204: None})
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_password(self, request, *args, **kwargs):
        """设置密码"""

        serializer = SetPasswordRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if not check_password(validated_data['old_password'], self.user.password):
            raise AuthenticationFailed('密码错误')

        self.user.password = make_password(validated_data['new_password'])
        self.user.save(update_fields=['password'])

        return Response(status=status.HTTP_200_OK)


__all__ = [
    'UserViewSet', 'UserActionViewSet',
]
