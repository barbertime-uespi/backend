from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsBarbeiroOrAdminOrReadOnly(BasePermission):
    """
    Leitura (GET, HEAD, OPTIONS) liberada para qualquer pessoa.
    Escrita (POST, PUT, PATCH, DELETE) restrita a barbeiros ou administradores.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        return user.is_staff or hasattr(user, 'barbeiro')