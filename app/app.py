from flask import Flask, request, abort
from sh import git
import os , logging , subprocess , shutil , json_file_builder, sys
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

@app.route('/test', methods=['GET']) 
def test():
    if request.method == 'GET' :
        return '<h1> Your docker container is running </h1>', 200
    
    else:
        abort(400)


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST' and request.json is not None:
         
        s3 = boto3.client('s3')
        payload = request.json
        user_name = payload['repository']['owner']['username']
        repo_name = payload['repository']['name']
        repo_clone_url = payload['repository']['clone_url']
        
        return clone_and_check_repo(user_name,repo_name, repo_clone_url, s3)

    else:
        abort(400)

def upload_file(user_name, repo_name, suffix, s3):      
    localfilename = f'./{repo_name}{suffix}.json'
    remotefilename = f'{user_name}/{repo_name}{suffix}.json'
    bucket_name = 'test-repo-badges-bucket'
    
    try :
        response = s3.upload_file(localfilename, bucket_name, remotefilename, ExtraArgs={'ACL':'public-read'})
    
    except ClientError as e: 
        logging.error(e)

def clone_and_check_repo(user_name, repo_name, repo_clone_url, s3):
        has_manifest = False

        try :
            os.makedirs('./tmp')
            os.chdir('./tmp')
            git.clone(repo_clone_url)
        
            for fname in os.listdir(f'./{repo_name}'):
                if fname == 'manifest.json' or fname == 'manifest.yaml':
                    has_manifest = True

            manifest_suffix = ""

            json_file_builder.get_has_manifest(repo_name=repo_name,suffix=manifest_suffix,is_valid=has_manifest)
            
            upload_file(user_name, repo_name, manifest_suffix, s3)
            os.chdir('../')

            try: 
                shutil.rmtree('./tmp')
                
            except OSError as e:  ## if failed, report it back to the user ##
                print ("Error: %s - %s." % (e.filename, e.strerror))
  
            
        except :
            e = sys.exc_info()[0]
            print("<p> Error: %s </p>" % e)
            os.chdir('/webhooks')
            shutil.rmtree('./tmp')

        return str(has_manifest), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)