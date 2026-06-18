

###################################################################################################


# Before you start

	# Install Anaconda Distribution: https://www.anaconda.com/download/success?reg=skipped


###################################################################################################



##### INSTALLATION GUIDE FOR NEUROMORPHIC WIZARD #####


# 0. Unzip the NeuromorphicWizard folder


# 1. Open Terminal (Mac) or Anaconda PowerShell Prompt (Windows) as Administrator and set directory to the 
     NeuromorphicWizard folder. 
 
	cd <YourPathnameHere>


	To find the pathname for the NeuromorphicWizard folder, right click the folder and on macOS hold down 
	the option key and select "Copy "NeuromorphicWizard" as Pathname" or on Windows right click while holding
	the shift key and select "Copy as path"


# 2. Create a new virtual environment with conda:

	conda create -n neuro_wiz python==3.10
	conda activate neuro_wiz

	# if you encounter the error "CondaError: Run 'conda init' before 'conda activate'" then restart
	  your shell using either 'source ~/.bashrc' or 'source ~/.zshrc' and try again

# 3. Install dependencies

	pip install -r requirements.txt


# 4. Run tests (optional)

	pytest tests/ -v


# 5. Start the application
	python3 main.py

	# if you encounter an error 'Python was not found', then try this command: python main.py

The next time you'd like to start the NeuromorphicWizard, type into Terminal or PowerShell:

	cd <YourPathnameHere>/NeuromorphicWizard
	conda activate neuro_wiz
	python3 main.py	