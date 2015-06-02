# Installing probespawner
1. Install the JAVA Runtime Engine - https://java.com/en/download/
2. Install Jython - http://www.jython.org/downloads.html
3. Install Probespawner - https://github.com/filipealmeida/probespawner
4. Run `probespawner.bat example.json` to test

## 1. Install the JAVA Runtime Engine
Download the JRE from https://java.com/en/download/ and install it on your system.  

## 2. Install Jython
Download Jython from http://www.jython.org/downloads.html  
Install the "standard type" as shown in the summary screen below:  
![](https://github.com/filipealmeida/probespawner/blob/master/docs/install.jython.5.png)
  
Setup the path for jython and give it a test run:  
![](https://github.com/filipealmeida/probespawner/blob/master/docs/install.jython.9.png)

## 3. Install Probespawner
After downloading the zipfile from https://github.com/filipealmeida/probespawner, uncompress the file to a folder of your choice.  
![](https://github.com/filipealmeida/probespawner/blob/master/docs/uncompress.probespawner.0.png)
  
We're choosing `C:\` where the `probespawner-master` directory with the Probespawner's code will be created.
![](https://github.com/filipealmeida/probespawner/blob/master/docs/uncompress.probespawner.1.png)

## 4. Run Probespawner
With Jython on your path (see step 2), from the command prompt on Probespawner's directory, run:  
`probespawner.bat example.json`  
![](https://github.com/filipealmeida/probespawner/blob/master/docs/run.probespawner.example.png)  
  
`example.json` has a `TestProbe` input configured that echos the following JSON string: `{"test":"Yes"}`  
The blue highlighted rectangles on the image show this sign of success.  
