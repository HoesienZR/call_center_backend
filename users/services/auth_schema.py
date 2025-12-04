from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

# ---------- CustomAuthToken ----------
auth_token_post_schema = extend_schema(
    tags=['Auth'],
    summary='Obtain auth token',
    description='Login with username/password and obtain auth token.',
    request={
        "application/json": {
            "username": "string",
            "password": "string",
        }
    },
    examples=[
        OpenApiExample(
            name="Request Example",
            summary="Request body example",
            value={
                "username": "admin",
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
                        "username": "admin",
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
                    summary="Missing username/password",
                    value={"error": "Username and password are required"},
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
                        "username": "admin",
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
                        "username": "admin",
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
    description='Create a new user with username, phone, and password.',
    request={
        "application/json": {
            "username": "string",
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
                "username": "newuser",
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
                        "username": "newuser",
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
                    summary="Username or phone already taken",
                    value={"error": "Username is already taken"},
                    response_only=True
                )
            ]
        )
    }
)

# ---------- request_otp ----------
request_otp_post_schema = extend_schema(
    tags=['Auth'],
    summary='Request OTP',
    description='Send OTP to user phone number.',
    request={
        "application/json": {
            "phone": "string"
        }
    },
    examples=[
        OpenApiExample(
            name="Request Example",
            summary="Request OTP example",
            value={"phone": "09121234567"},
            request_only=True
        )
    ],
    responses={
        200: OpenApiResponse(
            description="OTP sent",
            examples=[
                OpenApiExample(
                    name="Success",
                    summary="OTP sent",
                    value={"message": "OTP code sent"},
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(description="Phone number required"),
        404: OpenApiResponse(description="User not found"),
        429: OpenApiResponse(description="Too many requests")
    }
)

# ---------- verify_otp ----------
verify_otp_post_schema = extend_schema(
    tags=['Auth'],
    summary='Verify OTP',
    description='Verify OTP code sent to user phone and obtain auth token.',
    request={
        "application/json": {
            "phone": "string",
            "otp": "string"
        }
    },
    examples=[
        OpenApiExample(
            name="Request Example",
            summary="Verify OTP request example",
            value={"phone": "09121234567", "otp": "123456"},
            request_only=True
        )
    ],
    responses={
        200: OpenApiResponse(
            description="OTP verified, token returned",
            examples=[
                OpenApiExample(
                    name="Success",
                    summary="OTP verified",
                    value={
                        "token": "abcd1234token",
                        "user_id": 1,
                        "username": "admin",
                        "phone": "09121234567"
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid or expired OTP"),
        404: OpenApiResponse(description="User not found")
    }
)
