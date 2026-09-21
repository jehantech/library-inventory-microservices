pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Environment Check') {
            steps {
                bat 'git --version'
                bat 'docker --version'
                bat '"C:\\Users\\jehan\\AppData\\Local\\Programs\\DockerDesktop\\resources\\cli-plugins\\docker-compose.exe" version'
            }
        }

        stage('Build Docker Images') {
            steps {
                bat '"C:\\Users\\jehan\\AppData\\Local\\Programs\\DockerDesktop\\resources\\cli-plugins\\docker-compose.exe" -f docker-compose.yml build'
            }
        }

        stage('Deploy') {
    	    steps {
                bat '"C:\\Users\\jehan\\AppData\\Local\\Programs\\DockerDesktop\\resources\\cli-plugins\\docker-compose.exe" -p   devproject -f docker-compose.yml up -d'
           }
        }

        stage('Check Services') {
    	     steps {
                 bat '"C:\\Users\\jehan\\AppData\\Local\\Programs\\DockerDesktop\\resources\\cli-plugins\\docker-compose.exe" -p devproject -f docker-compose.yml ps'
           }
        }
    }
}