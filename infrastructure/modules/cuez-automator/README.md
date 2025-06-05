# CUEZ PROXY VM

Currently the Automator runs on MacOS or Windows. We have to spin up
this VM and then install the Automator via RDP, set the program and binding
then let the Cloud Run Proxy interact with the model.

## Instructions

When terraform has created the VM you will need to set the Windows Password
so you can actually log in.

You can do that in the UI, clicking on the vertical stacked option dots.

You'll set the username, it will then provide the password. Store it securely
somewhere.

You'll need an RDP client. Here are some options.

Several good RDP clients are available for macOS. Here are a few popular and well-regarded options:

Microsoft Remote Desktop: This is Microsoft's official RDP client and is generally a solid choice. It's free, well-integrated with macOS, and supports many features.

Royal TSX: This is a more advanced and feature-rich option suitable for managing multiple remote connections. It supports RDP, SSH, VNC, and other protocols. It's a commercial product but offers a free trial.

Jump Desktop: Another excellent commercial RDP client with a good user interface, solid performance, and support for various remote desktop protocols. It also offers a free trial.

RDM (Remote Desktop Manager): A very comprehensive, cross-platform remote connection manager suitable for IT professionals. It supports a wide range of protocols, including RDP, SSH, and VNC. RDM is a commercial product, with various licensing options available.

Once you have an RDP client installed, follow these steps:

1. **Obtain the VM's public IP address:** This is usually available in the Terraform output after the deployment completes.  It will be the external IP address assigned to the VM.

2. **Establish an RDP connection:** Open your RDP client and enter the VM's public IP address.  You may also need to specify the port (usually 3389, but check your Terraform configuration if it's different).

3. **Authenticate:** Use the username and password you set for the VM.  Remember to keep this password secure.

4. **Install the Automator:** Once connected, you can install the CUEZ Automator application on the Windows VM. Follow the installation instructions for the Automator.

5. **Configure the Automator:** Configure the Automator application according to its documentation. This will typically involve setting the API endpoint and other necessary parameters.

6. **Test the connection:** After installation and configuration, test the connection between the Automator and the Cloud Run proxy to ensure everything is working correctly.

Once connected you will need to [download the automator](https://download.cuez.app/automator/stable/latest)

Then you will need to open that port up to inbound requests on the Windows Firewall.
