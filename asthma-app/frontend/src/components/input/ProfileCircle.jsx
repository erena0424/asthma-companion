import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

function ProfileCircle({
  imageUrl,
  onClick,
  size = 88,
  disabled,
  ariaLabel,
  theme =""
}) {
    const { user } = useAuth();
    const [imageError, setImageError] = useState(false);

    const showImage = imageUrl && !imageError;

    return (
        <div
            className={`profile-circle ${theme}`}
            style={{
                width: size,
                height: size,
                cursor: onClick ? "pointer" : "default",
            }}
            onClick={onClick}
            disabled={disabled}
            aria-label={ariaLabel}
        >
        {
            showImage ? (
            <img
                src={imageUrl}
                alt=""
                className="profile-image"
                onError={() => setImageError(true)}
            />
            ) : (
            <div className="profile-default">
                <span>
                    {user?.name?.charAt(0).toUpperCase() || "?"}
                </span>
            </div>
            )
        }
        </div>
    );
}

export default ProfileCircle;