package predicttest.parts;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.Map;

import org.eclipse.swt.SWT;
import org.eclipse.swt.browser.Browser;
import org.eclipse.swt.layout.GridData;
import org.eclipse.swt.layout.GridLayout;
import org.eclipse.swt.widgets.Button;
import org.eclipse.swt.widgets.Composite;
import org.eclipse.swt.widgets.DirectoryDialog;
import org.eclipse.swt.widgets.Display;
import org.eclipse.swt.widgets.FileDialog;
import org.eclipse.swt.widgets.Label;
import org.eclipse.swt.widgets.Text;
import org.eclipse.ui.part.ViewPart;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class VideoUploadView extends ViewPart {
	public static final String ID = "predicttest.parts.VideoUploadView";
	private Text videoPathText;
	private Text jsonUrlText;
	private Text outputFolderText; // Output video folder path
	private Text infoText;
	private Button distanceButton;
	private Button speedButton;
	private Button weatherButton;
	private Browser videoPlayer;

	@Override
	public void createPartControl(Composite parent) {
		// Create the GridLayout parent with 3 columns
		parent.setLayout(new GridLayout(3, false));

		// Upload Video Label and Text Field
		Label lblUpload = new Label(parent, SWT.NONE);
		lblUpload.setText("Input Video:");

		videoPathText = new Text(parent, SWT.BORDER);
		videoPathText.setLayoutData(new GridData(SWT.FILL, SWT.CENTER, true, false));

		Button btnBrowse = new Button(parent, SWT.PUSH);
		btnBrowse.setText("Browse...");
		btnBrowse.addListener(SWT.Selection, e -> {
			FileDialog dialog = new FileDialog(parent.getShell(), SWT.OPEN);
			dialog.setFilterExtensions(new String[] { "*.mp4", "*.avi" });
			String videoPath = dialog.open();
			if (videoPath != null) {
				videoPathText.setText(videoPath);
			}
		});

		// JSON URL Label and Text Field
		Label lblJsonUrl = new Label(parent, SWT.NONE);
		lblJsonUrl.setText("Json File:");

		jsonUrlText = new Text(parent, SWT.BORDER);
		jsonUrlText.setLayoutData(new GridData(SWT.FILL, SWT.CENTER, true, false));

		Button btnBrowseFolder = new Button(parent, SWT.PUSH);
		btnBrowseFolder.setText("Browse...");
		btnBrowseFolder.addListener(SWT.Selection, e -> {
			DirectoryDialog dialog = new DirectoryDialog(parent.getShell(), SWT.OPEN);
			String selectedFolderPath = dialog.open();
			if (selectedFolderPath != null) {
				jsonUrlText.setText(selectedFolderPath);
			}
		});

		// Output Video Folder URL Label and Text Field
		Label lblOutputFolder = new Label(parent, SWT.NONE);
		lblOutputFolder.setText("Output Video:");

		outputFolderText = new Text(parent, SWT.BORDER);
		outputFolderText.setLayoutData(new GridData(SWT.FILL, SWT.CENTER, true, false));

		Button btnBrowseOutputFolder = new Button(parent, SWT.PUSH);
		btnBrowseOutputFolder.setText("Browse...");
		btnBrowseOutputFolder.addListener(SWT.Selection, e -> {
			DirectoryDialog dialog = new DirectoryDialog(parent.getShell(), SWT.OPEN);
			String selectedFolderPath = dialog.open();
			if (selectedFolderPath != null) {
				outputFolderText.setText(selectedFolderPath);
			}
		});

		// Add a space for the Select Algorithm label
		Label lblSelectAlgorithm = new Label(parent, SWT.NONE);
		lblSelectAlgorithm.setText("Select Algorithm:");
		GridData gridData = new GridData(SWT.FILL, SWT.CENTER, true, false);
		gridData.horizontalSpan = 3;
		lblSelectAlgorithm.setLayoutData(gridData);

		// Create a composite to hold the radio buttons
		Composite radioComposite = new Composite(parent, SWT.NONE);
		GridLayout radioLayout = new GridLayout(3, false);
		radioComposite.setLayout(radioLayout);
		radioComposite.setLayoutData(new GridData(SWT.FILL, SWT.CENTER, true, false, 3, 1));

		speedButton = new Button(radioComposite, SWT.RADIO);
		speedButton.setText("Speed Estimation");

		distanceButton = new Button(radioComposite, SWT.RADIO);
		distanceButton.setText("Distance Estimation");

		weatherButton = new Button(radioComposite, SWT.RADIO);
		weatherButton.setText("Weather Estimation");

		// Add the "Process Video" button after the browse folder button
		Button btnProcess = new Button(parent, SWT.PUSH);
		btnProcess.setText("Process Video");
		GridData processButtonGridData = new GridData(SWT.FILL, SWT.CENTER, true, false);
		processButtonGridData.horizontalSpan = 3;
		btnProcess.setLayoutData(processButtonGridData);
		btnProcess.addListener(SWT.Selection, e -> {
			String videoPath = videoPathText.getText();
			String jsonUrl = jsonUrlText.getText();
			String outputFolderPath = outputFolderText.getText();
			if (!videoPath.isEmpty() && !jsonUrl.isEmpty() && !outputFolderPath.isEmpty()) {
				String scriptName = null;
				if (distanceButton.getSelection()) {
					scriptName = "distance-detection.py";
				} else if (speedButton.getSelection()) {
					scriptName = "speed-estimation.py";
				} else if (weatherButton.getSelection()) {
					scriptName = "weather.py";
				}
				if (scriptName != null) {
					runPythonScript(scriptName, videoPath, jsonUrl, outputFolderPath);
				}
			}
		});

		// Create the mainComposite to organize the layout
		Composite mainComposite = new Composite(parent, SWT.NONE);
		GridLayout mainLayout = new GridLayout(2, true);
		mainComposite.setLayout(mainLayout);
		mainComposite.setLayoutData(new GridData(SWT.FILL, SWT.FILL, false, true, 3, 1));

		// Blue Zone: Information Label
		Label infoLabel = new Label(mainComposite, SWT.NONE);
		infoLabel.setText("Information:");
		GridData infoLabelData = new GridData(SWT.LEFT, SWT.TOP, false, false);
		infoLabelData.widthHint = 100;
		infoLabel.setLayoutData(infoLabelData);
		new Label(mainComposite, SWT.NONE);
		// Green Zone: Information Display (Text Widget)
		infoText = new Text(mainComposite, SWT.MULTI | SWT.BORDER | SWT.V_SCROLL | SWT.WRAP);
		GridData infoTextData = new GridData(SWT.FILL, SWT.FILL, true, true, 1, 1);
		infoText.setLayoutData(infoTextData);

		// Red Zone: Video Display (Browser Widget)
		videoPlayer = new Browser(mainComposite, SWT.NONE);
		GridData videoData = new GridData(SWT.FILL, SWT.FILL, true, true, 1, 2);
		videoPlayer.setLayoutData(videoData);
	}

	private void runPythonScript(String scriptName, String videoPath, String jsonUrl, String outputFolderPath) {
		String pythonScriptPath = "C:/Users/hsanm/Bureau/stage/" + scriptName;
		try {
			ProcessBuilder processBuilder = new ProcessBuilder("python", pythonScriptPath, videoPath, jsonUrl,
					outputFolderPath);
			processBuilder.redirectErrorStream(true);
			Process process = processBuilder.start();

			BufferedReader in = new BufferedReader(new InputStreamReader(process.getInputStream()));
			String line;
			while ((line = in.readLine()) != null) {
				// Debug print statement
				System.out.println(line);
			}
			in.close();
			process.waitFor();

			// Après l'exécution du script, lire et afficher le JSON
			if (!jsonUrl.isEmpty()) {
				if (scriptName.equals("weather.py")) {
					displayWeatherJsonContent(jsonUrl);
				} else {
					displayJsonContent(jsonUrl);
				}
			}

			// Charger la vidéo de sortie après traitement
			// Utilisez le champ de texte outputFolderText pour obtenir l'URL complète
			String outputVideoPath = outputFolderText.getText();
			if (!outputVideoPath.isEmpty()) {
				loadOutputVideo(outputVideoPath);
			}

		} catch (IOException | InterruptedException e) {
			e.printStackTrace();
		}
	}

	private void loadOutputVideo(String outputVideoPath) {
		// Convertir le chemin du fichier en URL absolue
		String videoUrl = outputVideoPath.replace("\\", "/");
		if (!videoUrl.startsWith("file://")) {
			videoUrl = "file://" + videoUrl;
		}

		// Appeler une méthode pour mettre à jour le videoPlayer
		updateVideoPlayer(videoUrl);
	}

	private void updateVideoPlayer(String videoUrl) {
		Display.getDefault().asyncExec(() -> {
			String html = "<html><body><video width='100%' height='100%' controls>" +
					"<source src='" + videoUrl + "' type='video/mp4'>" +
					"Your browser does not support the video tag." +
					"</video></body></html>";
			videoPlayer.setText(html);
		});
	}

	private void displayJsonContent(String jsonFilePath) {
		String parsedJson = parseJson(jsonFilePath);

		// Display the parsed JSON content in the infoText widget
		Display.getDefault().asyncExec(() -> infoText.setText(parsedJson));
	}

	private void displayWeatherJsonContent(String jsonFilePath) {
		String parsedJson = parseWeatherJson(jsonFilePath);

		// Display the parsed JSON content in the infoText widget
		Display.getDefault().asyncExec(() -> infoText.setText(parsedJson));
	}

	// Method to parse JSON and return formatted string
	private String parseJson(String filePath) {
		StringBuilder result = new StringBuilder();

		try (FileReader reader = new FileReader(filePath)) {
			JsonElement jsonElement = JsonParser.parseReader(reader);
			JsonObject jsonObject = jsonElement.getAsJsonObject();

			for (Map.Entry<String, JsonElement> entry : jsonObject.entrySet()) {
				String key = entry.getKey();
				JsonArray jsonArray = entry.getValue().getAsJsonArray();

				for (JsonElement element : jsonArray) {
					JsonObject jsonObjectValue = element.getAsJsonObject();
					String timestamp = jsonObjectValue.get("timestamp").getAsString();

					if (jsonObjectValue.has("speed")) {
						String speedStr = jsonObjectValue.get("speed").getAsString();
						// Remove " km/h" and parse the remaining string to double
						double speed = Double.parseDouble(speedStr.replace(" km/h", ""));
						result.append("ID: ").append(key).append(" - Timestamp: ").append(timestamp)
								.append(" - Speed: ").append(speed).append(" km/h\n");
					} else if (jsonObjectValue.has("distance")) {
						double distance = jsonObjectValue.get("distance").getAsDouble();
						result.append("ID: ").append(key).append(" - Timestamp: ").append(timestamp)
								.append(" - Distance: ").append(distance).append("\n");
					}
				}
			}

		} catch (IOException e) {
			e.printStackTrace();
		}

		return result.toString();
	}

	// Method to parse Weather JSON and return formatted string
	private String parseWeatherJson(String filePath) {
		StringBuilder result = new StringBuilder();

		try (FileReader reader = new FileReader(filePath)) {
			JsonElement jsonElement = JsonParser.parseReader(reader);
			JsonArray jsonArray = jsonElement.getAsJsonArray();

			for (JsonElement element : jsonArray) {
				JsonObject jsonObject = element.getAsJsonObject();
				String condition = jsonObject.get("condition").getAsString();
				String timestamp = jsonObject.get("timestamp").getAsString();

				result.append("Timestamp: ").append(timestamp).append(" - Condition: ").append(condition).append("\n");
			}

		} catch (IOException e) {
			e.printStackTrace();
		}

		return result.toString();
	}

	@Override
	public void setFocus() {
		// Set focus if needed
	}
}
