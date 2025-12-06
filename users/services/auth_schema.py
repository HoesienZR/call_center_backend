from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

# ---------- CustomAuthToken ----------
auth_token_post_schema = extend_schema(
    tags=['Auth'],
    summary='Obtain auth token',
    description='Login with phone/password and obtain auth token.',
    request={
        "application/json": {
            "phone": "string",
            "password": "string",
        }
    },
    examples=[
        OpenApiExample(
            name="Request Example",
            summary="Request body example",
            value={
                "phone": "admin",
                "password": "strongpassword123"
            },
            request_only=True
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Token returned",
            examples=[
                OpenApiExample(
                    name="Success",
                    summary="Successful login",
                    value={
                        "token": "abcd1234token",
                        "user_id": 1,
                        "email": "admin@example.com",
                        "is_staff": True,
                        "is_superuser": False,
                        "full_name": "Admin User"
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid input",
            examples=[
                OpenApiExample(
                    name="MissingFields",
                    summary="Missing password",
                    value={"error": "password are required"},
                    response_only=True
                )
            ]
        )
    }
)

# ---------- login ----------
login_post_schema = extend_schema(
    tags=['Auth'],
    summary='Login with phone number',
    description='Login using phone number and password. Returns auth token.',
    request={
        "application/json": {
            "phone": "string",
            "password": "string",
        }
    },
    examples=[
        OpenApiExample(
            name="Request Example",
            summary="Request body example",
            value={
                "phone": "09121234567",
                "password": "strongpassword123"
            },
            request_only=True
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Token returned",
            examples=[
                OpenApiExample(
                    name="Success",
                    summary="Successful login",
                    value={
                        "token": "abcd1234token",
                        "user_id": 1,
                        "email": "admin@example.com",
                        "is_staff": True,
                        "is_superuser": False,
                        "full_name": "Admin User",
                        "phone": "09121234567"
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Phone number and password required",
            examples=[
                OpenApiExample(
                    name="MissingFields",
                    summary="Missing phone or password",
                    value={"error": "Phone number and password are required"},
                    response_only=True
                )
            ]
        ),
        401: OpenApiResponse(
            description="Unauthorized",
            examples=[
                OpenApiExample(
                    name="Unauthorized",
                    summary="Invalid credentials",
                    value={"error": "Phone number or password is incorrect"},
                    response_only=True
                )
            ]
        )
    }
)

# ---------- logout ----------
logout_post_schema = extend_schema(
    tags=['Auth'],
    summary='Logout user',
    description='Deletes user token to logout.',
    responses={
        200: OpenApiResponse(
            description="Successfully logged out",
            examples=[
                OpenApiExample(
                    name="Success",
                    summary="Logout success",
                    value={"message": "Successfully logged out"},
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Valid token not found",
            examples=[
                OpenApiExample(
                    name="Error",
                    summary="Token missing",
                    value={"error": "Valid token not found"},
                    response_only=True
                )
            ]
        )
    }
)

# ---------- user_profile ----------
user_profile_get_schema = extend_schema(
    tags=['Auth'],
    summary='Get user profile',
    description='Retrieve profile of currently logged-in user.',
    responses={
        200: OpenApiResponse(
            description="User profile",
            examples=[
                OpenApiExample(
                    name="Profile",
                    summary="User profile data",
                    value={
                        "id": 1,
                        "email": "admin@example.com",
                        "first_name": "Admin",
                        "last_name": "User",
                        "phone_number": "09121234567"
                    },
                    response_only=True
                )
            ]
        ),
        401: OpenApiResponse(
            description="Unauthorized",
            examples=[
                OpenApiExample(
                    name="Unauthorized",
                    summary="User not logged in",
                    value={"detail": "Authentication credentials were not provided."},
                    response_only=True
                )
            ]
        )
    }
)

# ---------- register ----------
register_post_schema = extend_schema(
    tags=['Auth'],
    summary='Register new user',
    description='Create a new user with phone, and password.',
    request={
        "application/json": {
            "password": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string",
            "phone_number": "string"
        }
    },
    examples=[
        OpenApiExample(
            name="Request Example",
            summary="Request body example",
            value={
                "password": "strongpassword123",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "phone_number": "09123456789"
            },
            request_only=True
        )
    ],
    responses={
        201: OpenApiResponse(
            description="User created",
            examples=[
                OpenApiExample(
                    name="Success",
                    summary="User successfully created",
                    value={
                        "message": "User successfully created",
                        "token": "abcd1234token",
                        "user_id": 2,
                        "email": "newuser@example.com"
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid input or user exists",
            examples=[
                OpenApiExample(
                    name="UserExists",
                    summary="phone already taken",
                    value={"error": "phone is already taken"},
                    response_only=True
                )
            ]
        )
    }
)

# ---------- request_otp ----------
request_otp_post_schema = extend_schema(
    tags=["Auth"],
    summary="Request OTP Code",
    description="Send a one-time password (OTP) to the user's phone number.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "example": "09123456789"},
            },
            "required": ["phone"]
        }
    },
    responses={
        200: OpenApiResponse(
            description="OTP successfully sent.",
            response={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "example": "OTP sent"}
                }
            }
        ),
        400: OpenApiResponse(
            description="Phone number is missing",
            response={"type": "object", "properties": {"error": {"type": "string"}}},
        ),
        429: OpenApiResponse(
            description="OTP already sent and still valid",
            response={"type": "object", "properties": {"error": {"type": "string"}}},
        ),
    },
    examples=[
        OpenApiExample(
            "Successful Send",
            value={"phone": "09123456789"},
            request_only=True,
        )
    ],
)

# ---------- verify_otp ----------
verify_otp_post_schema = extend_schema(
    tags=["Auth"],
    summary="Verify OTP and Login",
    description="Verifies the received OTP code and returns an auth token.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "example": "09123456789"},
                "otp": {"type": "string", "example": "123456"},
            },
            "required": ["phone", "otp"]
        }
    },
    responses={
        200: OpenApiResponse(
            description="OTP verified successfully, user authenticated.",
            response={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "example": "5aa127f75b214d0c9a5afdb3f5a12345"},
                    "user_id": {"type": "integer", "example": 1},
                    "phone": {"type": "string", "example": "09123456789"},
                }
            }
        ),
        400: OpenApiResponse(
            description="Invalid or expired OTP",
            response={"type": "object", "properties": {"error": {"type": "string"}}}
        ),
        404: OpenApiResponse(
            description="User not found",
            response={"type": "object", "properties": {"error": {"type": "string"}}}
        ),
    },
    examples=[
        OpenApiExample(
            "Verify OTP Example",
            value={"phone": "09123456789", "otp": "123456"},
            request_only=True,
        )
    ]
)

