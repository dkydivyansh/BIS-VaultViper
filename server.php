<?php
// Define the folder where the files will be saved
$upload_dir = 'user-data/';

// Check if the folder exists, if not, create it
if (!file_exists($upload_dir)) {
    mkdir($upload_dir, 0777, true);
}

// Check if a file was uploaded
if (isset($_FILES['zip_file']) && $_FILES['zip_file']['error'] == 0) {
    // Get the current time and date
    $current_time = date('Y-m-d_H-i-s');
    
    // Get the file extension
    $file_extension = pathinfo($_FILES['zip_file']['name'], PATHINFO_EXTENSION);

    // Create a new file name with current time and date
    $new_file_name = $current_time . '.' . $file_extension;

    // Full path to save the file
    $target_file = $upload_dir . $new_file_name;

    // Move the uploaded file to the target folder
    if (move_uploaded_file($_FILES['zip_file']['tmp_name'], $target_file)) {
        echo json_encode(["status" => "success", "message" => "File uploaded and saved as $new_file_name"]);
    } else {
        echo json_encode(["status" => "error", "message" => "Failed to move the uploaded file."]);
    }
} else {
    echo json_encode(["status" => "error", "message" => "No file uploaded or there was an error uploading the file."]);
}
?>
