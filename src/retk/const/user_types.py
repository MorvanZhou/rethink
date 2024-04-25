from dataclasses import dataclass


@dataclass
class UserConfig:
    id: int
    max_store_space: int


_mb = 1024 * 1024
_gb = 1024 * _mb


class UserType:
    NORMAL = UserConfig(
        id=0,
        max_store_space=500 * _mb,  # 500MB
    )
    ADMIN = UserConfig(
        id=1,
        max_store_space=100 * _gb,  # 100GB
    )
    MANAGER = UserConfig(
        id=2,
        max_store_space=10 * _gb,  # 10GB
    )

    def id2config(self, _id: int):
        if _id == self.NORMAL.id:
            return self.NORMAL
        elif _id == self.ADMIN.id:
            return self.ADMIN
        elif _id == self.MANAGER.id:
            return self.MANAGER
        else:
            raise ValueError(f"Invalid user type: {_id}")


USER_TYPE = UserType()
