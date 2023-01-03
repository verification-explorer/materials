import argparse
from collections import defaultdict
import face_recognition
import pathlib
import pickle
from PIL import Image, ImageDraw


DEFAULT_ENCODINGS_PATH = "output/encodings.pkl"


parser = argparse.ArgumentParser(description="Recognize faces in an image")
parser.add_argument("--train", action="store_true", help="Train on input data")
parser.add_argument(
    "--validate", action="store_true", help="Validate trained model"
)
parser.add_argument(
    "--test", action="store_true", help="Test the model with an unknown image"
)
parser.add_argument(
    "-m",
    action="store",
    default="hog",
    choices=["hog", "cnn"],
    help="Which model to use for training: hog (CPU), cnn (GPU)",
)
parser.add_argument(
    "-f", action="store", help="Unknown image filename within eval_img/"
)
args = parser.parse_args()


def encode_known_faces(
    model: str, encodings_location: str = DEFAULT_ENCODINGS_PATH
) -> None:
    names = []
    encodings = []
    for filepath in pathlib.Path("training").glob("*/*"):
        name = filepath.parts[1]
        image = face_recognition.load_image_file(filepath)

        # Detect faces in loaded image
        face_locations = face_recognition.face_locations(
            image, model=model
        )  # Can use cnn if on GPU for more accuracy

        # Use bounding boxes to get face encodings.
        face_encodings = face_recognition.face_encodings(image, face_locations)
        for encoding in face_encodings:
            names.append(name)
            encodings.append(encoding)

    name_encodings = {"names": names, "encodings": encodings}
    with open(encodings_location, "wb") as f:
        pickle.dump(name_encodings, f)


def recognize_faces(
    image_location: str,
    model: str = "hog",
    encodings_location: str = DEFAULT_ENCODINGS_PATH,
) -> None:
    with open(encodings_location, "rb") as f:
        loaded_encodings = pickle.load(f)

    input_image = face_recognition.load_image_file(image_location)

    # Detect faces in input and generate encodings
    input_face_locations = face_recognition.face_locations(
        input_image, model=model
    )
    input_face_encodings = face_recognition.face_encodings(
        input_image, input_face_locations
    )

    pillow_image = Image.fromarray(input_image)
    draw = ImageDraw.Draw(pillow_image)

    # Interpret
    for (top, right, bottom, left), unknown_encoding in zip(
        input_face_locations, input_face_encodings
    ):
        boolean_matches = face_recognition.compare_faces(
            loaded_encodings["encodings"], unknown_encoding
        )
        result = "Not found"

        # Generate a list of matched indexes
        match_indexes = []
        name_frequency = defaultdict(int)
        for index, match in enumerate(boolean_matches):
            if match:
                match_indexes.append(index)

        for index in match_indexes:
            name = loaded_encodings["names"][index]
            name_frequency[name] += 1

        # Get the highest-voted name
        if name_frequency:
            result = max(name_frequency, key=lambda key: name_frequency[key])

        # Draw box around detected face
        draw.rectangle(((left, top), (right, bottom)), outline=(51, 51, 255))
        caption_width, caption_height = draw.textsize(result)
        # Draw solid box to show result
        draw.rectangle(
            ((left, bottom - caption_height - 10), (right, bottom)),
            fill=(51, 51, 255),
            outline=(51, 51, 255),
        )
        # Write the results on the caption box and preserve margins
        draw.text(
            (left + 6, bottom - caption_height - 5),
            result,
            fill=(255, 255, 255, 255),
        )

    del draw
    pillow_image.show()


def validate(model: str = "hog"):
    for filepath in pathlib.Path("validation").glob("**/*"):
        recognize_faces(image_location=str(filepath), model=model)


if __name__ == "__main__":
    if args.train:
        encode_known_faces(model=args.m)
    if args.validate:
        validate(model=args.m)
    if args.test:
        recognize_faces(image_location=args.f, model=args.m)
