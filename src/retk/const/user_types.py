from dataclasses import dataclass


@dataclass
class UserConfig:
    id: int
    max_store_space: int


class UserType:
    NORMAL = UserConfig(
        id=0,
        max_store_space=1024 * 1024 * 500,  # 500MB
    )
    ADMIN = UserConfig(
        id=1,
        max_store_space=1024 * 1024 * 1024 * 100,  # 100GB
    )

    def id2config(self, _id: int):
        if _id == self.NORMAL.id:
            return self.NORMAL
        elif _id == self.ADMIN.id:
            return self.ADMIN
        else:
            raise ValueError(f"Invalid user type: {_id}")


USER_TYPE = UserType()
