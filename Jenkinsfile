pipeline {
    agent any

    stages {

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t myapp:build-${BUILD_NUMBER} .'
            }
        }

        stage('Run Application') {
            steps {
                sh 'docker rm -f myapp-jenkins-test 2>/dev/null || true'
                sh 'docker run -d --name myapp-jenkins-test --network devops-net -p 8082:8080 myapp:build-${BUILD_NUMBER}'
            }
        }

        stage('Test Application') {
            steps {
                sh '''
                docker run --rm \
                  --network devops-net \
                  python:3.12-slim \
                  python3 -c "import urllib.request; print(urllib.request.urlopen('http://myapp-jenkins-test:8080').read().decode())"
                '''
            }
        }
        stage('Test AWS Authentication') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                    aws sts get-caller-identity
                    '''
                }
            }
        }
	stage('Login to ECR') {
    	    steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                   )
               ]) {
                   sh '''
                   aws ecr get-login-password --region us-east-1 | \
                   docker login --username AWS --password-stdin \
                   361646636271.dkr.ecr.us-east-1.amazonaws.com
                   '''
                }
            }
        }
    }
}
