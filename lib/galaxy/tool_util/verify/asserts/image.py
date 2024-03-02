import io
from typing import (
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

try:
    import numpy
except ImportError:
    pass
try:
    from PIL import Image
except ImportError:
    pass

if TYPE_CHECKING:
    import numpy.typing


def assert_image_has_metadata(
    output_bytes: bytes,
    width: Optional[Union[int, str]] = None,
    height: Optional[Union[int, str]] = None,
    channels: Optional[Union[int, str]] = None,
) -> None:
    """
    Assert the image output has specific metadata.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:

        assert width is None or im.size[0] == int(width), f"Image has wrong width: {im.size[0]} (expected {int(width)})"

        assert height is None or im.size[1] == int(
            height
        ), f"Image has wrong height: {im.size[1]} (expected {int(height)})"

        actual_channels = len(im.getbands())
        assert channels is None or actual_channels == int(
            channels
        ), f"Image has wrong number of channels: {actual_channels} (expected {int(channels)})"


def _compute_center_of_mass(im_arr: "numpy.typing.NDArray") -> Tuple[float, float]:
    while im_arr.ndim > 2:
        im_arr = im_arr.sum(axis=2)
    im_arr = numpy.abs(im_arr)
    if im_arr.sum() == 0:
        return (numpy.nan, numpy.nan)
    im_arr = im_arr / im_arr.sum()
    yy, xx = numpy.indices(im_arr.shape)
    return (im_arr * xx).sum(), (im_arr * yy).sum()


def assert_image_has_intensities(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
    mean_intensity: Optional[Union[float, str]] = None,
    mean_intensity_min: Optional[Union[float, str]] = None,
    mean_intensity_max: Optional[Union[float, str]] = None,
    center_of_mass: Optional[Union[Tuple[float, float], str]] = None,
    eps: Union[float, str] = 0.01,
) -> None:
    """
    Assert the image output has specific intensity content.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        im_arr = numpy.array(im)

    # Select the specified channel (if any).
    if channel is not None:
        im_arr = im_arr[:, :, int(channel)]

    # Perform `mean_intensity` assertion.
    actual_mean_intensity = im_arr.mean()
    if mean_intensity is not None:
        mean_intensity = float(mean_intensity)
        assert abs(actual_mean_intensity - mean_intensity) <= float(
            eps
        ), f"Wrong mean intensity: {actual_mean_intensity} (expected {mean_intensity}, eps: {eps})"

    # Perform `mean_intensity_min` assertion.
    if mean_intensity_min is not None:
        mean_intensity_min = float(mean_intensity_min)
        assert (
            actual_mean_intensity >= mean_intensity_min
        ), f"Wrong mean intensity: {actual_mean_intensity} (mean_intensity_min: {mean_intensity_min})"

    # Perform `mean_intensity_max` assertion.
    if mean_intensity_max is not None:
        mean_intensity_max = float(mean_intensity_max)
        assert (
            actual_mean_intensity <= mean_intensity_max
        ), f"Wrong mean intensity: {actual_mean_intensity} (mean_intensity_max: {mean_intensity_max})"

    # Perform `center_of_mass` assertion.
    if center_of_mass is not None:
        if isinstance(center_of_mass, str):
            center_of_mass_parts = [c.strip() for c in center_of_mass.split(",")]
            assert len(center_of_mass_parts) == 2
            center_of_mass = (float(center_of_mass_parts[0]), float(center_of_mass_parts[1]))
        assert len(center_of_mass) == 2, "center_of_mass must have two components"
        actual_center_of_mass = _compute_center_of_mass(im_arr)
        distance = numpy.linalg.norm(numpy.subtract(center_of_mass, actual_center_of_mass))
        assert distance <= float(
            eps
        ), f"Wrong center of mass: {actual_center_of_mass} (expected {center_of_mass}, distance: {distance}, eps: {eps})"


def assert_image_has_labels(
    output_bytes: bytes,
    number_of_objects: Optional[Union[int, str]] = None,
    mean_object_size: Optional[Union[float, str]] = None,
    mean_object_size_min: Optional[Union[float, str]] = None,
    mean_object_size_max: Optional[Union[float, str]] = None,
    exclude_labels: Optional[Union[str, List[int]]] = None,
    eps: Union[float, str] = 0.01,
) -> None:
    """
    Assert the image output has specific label content.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        im_arr = numpy.array(im)

    # Determine labels present in the image.
    labels = numpy.unique(im_arr)

    # Apply filtering due to `exclude_labels`.
    if exclude_labels is None:
        exclude_labels = list()
    if isinstance(exclude_labels, str):

        def cast_label(label):
            if numpy.issubdtype(im_arr.dtype, numpy.integer):
                return int(label)
            if numpy.issubdtype(im_arr.dtype, float):
                return float(label)
            raise AssertionError(f'Unsupported image label type: "{im_arr.dtype}"')

        exclude_labels = [cast_label(label) for label in exclude_labels.split(",") if len(label) > 0]
    labels = [label for label in labels if label not in exclude_labels]

    # Perform `number_of_objects` assertion.
    if number_of_objects is not None:
        actual_number_of_objects = len(labels)
        expected_number_of_objects = int(number_of_objects)
        assert (
            actual_number_of_objects == expected_number_of_objects
        ), f"Wrong number of objects: {actual_number_of_objects} (expected {expected_number_of_objects})"

    # Perform `mean_object_size` assertion.
    actual_mean_object_size = sum((im_arr == label).sum() for label in labels) / len(labels)
    if mean_object_size is not None:
        expected_mean_object_size = float(mean_object_size)
        assert abs(actual_mean_object_size - expected_mean_object_size) <= float(
            eps
        ), f"Wrong mean object size: {actual_mean_object_size} (expected {expected_mean_object_size}, eps: {eps})"

    # Perform `mean_object_size_min` assertion.
    if mean_object_size_min is not None:
        mean_object_size_min = float(mean_object_size_min)
        assert (
            actual_mean_object_size >= mean_object_size_min
        ), f"Wrong mean object size: {actual_mean_object_size} (mean_object_size_min: {mean_object_size_min})"

    # Perform `mean_object_size_max` assertion.
    if mean_object_size_max is not None:
        mean_object_size_max = float(mean_object_size_max)
        assert (
            actual_mean_object_size <= mean_object_size_max
        ), f"Wrong mean object size: {actual_mean_object_size} (mean_object_size_max: {mean_object_size_max})"
